import 'package:verse_archive_translator_flutter/src/models/archive_models.dart';
import 'package:verse_archive_translator_flutter/src/storage/workspace_storage.dart';

class FakeWorkspaceStorage implements WorkspaceStorage {
  FakeWorkspaceStorage({required Map<String, String> files})
    : files = Map<String, String>.from(files) {
    var counter = 1;
    for (final path in this.files.keys) {
      _lastModified[path] = counter;
      counter += 1;
    }
  }

  final Map<String, String> files;
  final Map<String, int> _lastModified = <String, int>{};

  @override
  Future<List<DirectoryItem>> listDirectory({
    required String treeUri,
    String relativePath = '',
  }) async {
    final directory = _normalize(relativePath);
    final childNames = <String, _ChildEntry>{};

    for (final filePath in files.keys) {
      if (directory.isNotEmpty &&
          filePath != directory &&
          !filePath.startsWith('$directory/')) {
        continue;
      }

      final remaining = directory.isEmpty
          ? filePath
          : filePath.substring(directory.length + 1);
      if (remaining.isEmpty) {
        continue;
      }

      final firstSegment = remaining.split('/').first;
      final childPath = directory.isEmpty
          ? firstSegment
          : '$directory/$firstSegment';
      final isDirectory = remaining.contains('/');
      childNames[firstSegment] = _ChildEntry(
        relativePath: childPath,
        isDirectory: isDirectory,
      );
    }

    final items =
        childNames.entries
            .map((entry) {
              final child = entry.value;
              return DirectoryItem(
                name: entry.key,
                relativePath: child.relativePath,
                isDirectory: child.isDirectory,
                lastModified: _lastModified[child.relativePath] ?? 0,
                size: child.isDirectory
                    ? null
                    : files[child.relativePath]?.length,
              );
            })
            .toList(growable: false)
          ..sort((left, right) => left.name.compareTo(right.name));

    return items;
  }

  @override
  Future<PickedWorkspace?> pickWorkspace() async => null;

  @override
  Future<TextFileSnapshot> readTextFile({
    required String treeUri,
    required String relativePath,
  }) async {
    final path = _normalize(relativePath);
    final content = files[path];
    if (content == null) {
      throw const StorageException(
        message: 'File not found',
        code: 'not_found',
      );
    }

    return TextFileSnapshot(
      relativePath: path,
      name: basenameOfRelativePath(path),
      content: content,
      lastModified: _lastModified[path] ?? 0,
    );
  }

  @override
  Future<WriteTextResult> writeTextFileIfUnchanged({
    required String treeUri,
    required String relativePath,
    required int expectedLastModified,
    required String content,
  }) async {
    final path = _normalize(relativePath);
    final currentLastModified = _lastModified[path] ?? 0;
    if (expectedLastModified != currentLastModified) {
      throw const StorageException(message: 'stale write', code: 'stale');
    }

    files[path] = content;
    _lastModified[path] = currentLastModified + 1;
    return WriteTextResult(lastModified: _lastModified[path]!);
  }

  void replaceFile(
    String relativePath,
    String content, {
    bool bumpLastModified = true,
  }) {
    final path = _normalize(relativePath);
    files[path] = content;
    if (bumpLastModified) {
      _lastModified[path] = (_lastModified[path] ?? 0) + 1;
    }
  }

  int lastModifiedOf(String relativePath) {
    return _lastModified[_normalize(relativePath)] ?? 0;
  }

  String _normalize(String rawPath) {
    return rawPath.replaceAll('\\', '/').trim();
  }
}

WorkspaceBookmark sampleWorkspaceBookmark({
  String treeUri = 'workspace',
  String displayName = 'Workspace',
  String archiveRelativePath = '',
  String resolutionSource = 'selected_directory',
}) {
  return WorkspaceBookmark(
    treeUri: treeUri,
    displayName: displayName,
    archiveRelativePath: archiveRelativePath,
    resolutionSource: resolutionSource,
    lastOpenedAt: DateTime.parse('2026-04-15T12:00:00Z'),
  );
}

class _ChildEntry {
  const _ChildEntry({required this.relativePath, required this.isDirectory});

  final String relativePath;
  final bool isDirectory;
}
