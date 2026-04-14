package com.versearchive.verse_archive_translator_flutter

import android.app.Activity
import android.content.Intent
import android.net.Uri
import androidx.documentfile.provider.DocumentFile
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodCall
import io.flutter.plugin.common.MethodChannel
import java.io.FileNotFoundException

class MainActivity : FlutterActivity() {
    companion object {
        private const val CHANNEL_NAME =
            "com.versearchive.verse_archive_translator_flutter/workspace"
        private const val OPEN_DOCUMENT_TREE_REQUEST = 41027
    }

    private var pendingPickResult: MethodChannel.Result? = null

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)

        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, CHANNEL_NAME)
            .setMethodCallHandler { call, result ->
                when (call.method) {
                    "pickWorkspace" -> pickWorkspace(result)
                    "listDirectory" -> handleListDirectory(call, result)
                    "readTextFile" -> handleReadTextFile(call, result)
                    "writeTextFileIfUnchanged" -> handleWriteTextFile(call, result)
                    else -> result.notImplemented()
                }
            }
    }

    @Deprecated("Uses the classic activity result API for broader compatibility in this Flutter shell.")
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)

        if (requestCode != OPEN_DOCUMENT_TREE_REQUEST) {
            return
        }

        val result = pendingPickResult ?: return
        pendingPickResult = null

        if (resultCode != Activity.RESULT_OK) {
            result.success(null)
            return
        }

        val uri = data?.data
        if (uri == null) {
            result.success(null)
            return
        }

        try {
            val takeFlags =
                (data.flags and (Intent.FLAG_GRANT_READ_URI_PERMISSION or Intent.FLAG_GRANT_WRITE_URI_PERMISSION))
                    .takeIf { it != 0 }
                    ?: (Intent.FLAG_GRANT_READ_URI_PERMISSION or Intent.FLAG_GRANT_WRITE_URI_PERMISSION)
            applicationContext.contentResolver.takePersistableUriPermission(uri, takeFlags)

            result.success(
                mapOf(
                    "treeUri" to uri.toString(),
                    "displayName" to resolveDocumentName(uri),
                ),
            )
        } catch (error: SecurityException) {
            result.error(
                "permission_denied",
                "Unable to persist folder access permission.",
                error.message,
            )
        }
    }

    private fun pickWorkspace(result: MethodChannel.Result) {
        if (pendingPickResult != null) {
            result.error("busy", "Another folder picker request is already running.", null)
            return
        }

        pendingPickResult = result

        val intent = Intent(Intent.ACTION_OPEN_DOCUMENT_TREE).apply {
            addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
            addFlags(Intent.FLAG_GRANT_WRITE_URI_PERMISSION)
            addFlags(Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION)
            addFlags(Intent.FLAG_GRANT_PREFIX_URI_PERMISSION)
        }
        startActivityForResult(intent, OPEN_DOCUMENT_TREE_REQUEST)
    }

    private fun handleListDirectory(call: MethodCall, result: MethodChannel.Result) {
        val treeUri = call.requireStringArgument("treeUri", result) ?: return
        val relativePath = call.argument<String>("relativePath").orEmpty()

        try {
            val directory = resolveDocument(treeUri, relativePath)
            if (directory == null || !directory.isDirectory) {
                result.error("not_found", "Directory was not found.", relativePath)
                return
            }

            val children = directory.listFiles()
                .sortedBy { it.name.orEmpty() }
                .mapNotNull { child ->
                    val name = child.name ?: return@mapNotNull null
                    mapOf(
                        "name" to name,
                        "relativePath" to joinRelativePath(relativePath, name),
                        "isDirectory" to child.isDirectory,
                        "lastModified" to child.lastModified(),
                        "size" to if (child.isFile) child.length() else null,
                    )
                }

            result.success(children)
        } catch (error: Exception) {
            result.error("list_failed", "Failed to list directory contents.", error.message)
        }
    }

    private fun handleReadTextFile(call: MethodCall, result: MethodChannel.Result) {
        val treeUri = call.requireStringArgument("treeUri", result) ?: return
        val relativePath = call.requireStringArgument("relativePath", result) ?: return

        try {
            val file = resolveDocument(treeUri, relativePath)
            if (file == null || !file.isFile) {
                result.error("not_found", "File was not found.", relativePath)
                return
            }

            val content = applicationContext.contentResolver.openInputStream(file.uri)
                ?.bufferedReader(Charsets.UTF_8)
                ?.use { it.readText() }
                ?: throw FileNotFoundException(relativePath)

            result.success(
                mapOf(
                    "relativePath" to relativePath,
                    "name" to (file.name ?: relativePath.substringAfterLast('/')),
                    "content" to content,
                    "lastModified" to file.lastModified(),
                ),
            )
        } catch (error: Exception) {
            result.error("read_failed", "Failed to read file.", error.message)
        }
    }

    private fun handleWriteTextFile(call: MethodCall, result: MethodChannel.Result) {
        val treeUri = call.requireStringArgument("treeUri", result) ?: return
        val relativePath = call.requireStringArgument("relativePath", result) ?: return
        val content = call.requireStringArgument("content", result) ?: return
        val expectedLastModified = call.argument<Number>("expectedLastModified")?.toLong() ?: 0L

        try {
            val file = resolveDocument(treeUri, relativePath)
            if (file == null || !file.isFile) {
                result.error("not_found", "File was not found.", relativePath)
                return
            }

            val currentLastModified = file.lastModified()
            if (expectedLastModified > 0 && currentLastModified != expectedLastModified) {
                result.error("stale", "File changed before save.", currentLastModified.toString())
                return
            }

            applicationContext.contentResolver.openOutputStream(file.uri, "wt")
                ?.bufferedWriter(Charsets.UTF_8)
                ?.use { writer ->
                    writer.write(content)
                    writer.flush()
                }
                ?: throw FileNotFoundException(relativePath)

            val refreshed = resolveDocument(treeUri, relativePath) ?: file
            result.success(
                mapOf(
                    "lastModified" to refreshed.lastModified(),
                ),
            )
        } catch (error: Exception) {
            result.error("write_failed", "Failed to write file.", error.message)
        }
    }

    private fun resolveDocument(treeUriString: String, relativePath: String): DocumentFile? {
        val treeUri = Uri.parse(treeUriString)
        var current = DocumentFile.fromTreeUri(applicationContext, treeUri) ?: return null

        val segments = normalizeRelativePath(relativePath)
        for (segment in segments) {
            current = current.findFile(segment) ?: return null
        }

        return current
    }

    private fun resolveDocumentName(uri: Uri): String {
        val tree = DocumentFile.fromTreeUri(applicationContext, uri)
        val treeName = tree?.name
        if (!treeName.isNullOrBlank()) {
            return treeName
        }

        return uri.lastPathSegment?.substringAfterLast(':') ?: "workspace"
    }

    private fun normalizeRelativePath(relativePath: String): List<String> {
        val normalized = relativePath.replace("\\", "/").trim()
        if (normalized.isEmpty() || normalized == ".") {
            return emptyList()
        }

        return normalized.split("/")
            .map { it.trim() }
            .filter { it.isNotEmpty() && it != "." && it != ".." }
    }

    private fun joinRelativePath(base: String, name: String): String {
        val cleanBase = base.replace("\\", "/").trim()
        val cleanName = name.replace("\\", "/").trim()
        return when {
            cleanBase.isEmpty() -> cleanName
            cleanName.isEmpty() -> cleanBase
            else -> "$cleanBase/$cleanName"
        }
    }

    private fun MethodCall.requireStringArgument(
        key: String,
        result: MethodChannel.Result,
    ): String? {
        val value = argument<String>(key)?.trim()
        if (value.isNullOrEmpty()) {
            result.error("invalid_arguments", "Missing required argument: $key", null)
            return null
        }
        return value
    }
}
