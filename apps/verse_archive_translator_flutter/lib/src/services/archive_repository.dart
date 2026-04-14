import 'dart:convert';

import '../models/archive_models.dart';
import '../storage/workspace_storage.dart';

class RepositoryException implements Exception {
  const RepositoryException(this.message);

  final String message;

  @override
  String toString() => message;
}

class SaveTranslationResult {
  const SaveTranslationResult({
    required this.updatedDocument,
    required this.updatedEntry,
  });

  final ArchiveDocument updatedDocument;
  final ArchiveEntry updatedEntry;
}

class ArchiveRepository {
  ArchiveRepository(this._storage);

  final WorkspaceStorage _storage;

  Future<PickedWorkspace?> pickWorkspace() {
    return _storage.pickWorkspace();
  }

  Future<ResolvedArchiveDirectory> resolveArchiveDirectory({
    required String treeUri,
  }) async {
    final notes = <String>[];

    final settingsMap = await _tryReadJsonObject(
      treeUri: treeUri,
      relativePath: 'data/settings.json',
    );
    final desktopDataDir = _extractDesktopTranslationDataDir(settingsMap);
    if (desktopDataDir != null && desktopDataDir.isNotEmpty) {
      final normalized = normalizeRelativeDirectory(desktopDataDir);
      if (normalized != null) {
        final fromSettings = await _tryListArchiveFiles(
          treeUri: treeUri,
          archiveRelativePath: normalized,
        );
        if (fromSettings.isNotEmpty) {
          return ResolvedArchiveDirectory(
            archiveRelativePath: normalized,
            source: 'desktop_settings',
            notes: notes,
            desktopSettingValue: desktopDataDir,
          );
        }

        notes.add(
          '已讀取 data/settings.json 的 translation.data_dir，但該目錄下沒有找到 VerseArchiveTranslator JSON。',
        );
      } else {
        notes.add(
          'data/settings.json 的 translation.data_dir 無法在 Android SAF 下相對解析，已改用目前選取目錄或 output/ 嘗試載入。',
        );
      }
    }

    final selectedDirectory = await _tryListArchiveFiles(
      treeUri: treeUri,
      archiveRelativePath: '',
    );
    if (selectedDirectory.isNotEmpty) {
      return ResolvedArchiveDirectory(
        archiveRelativePath: '',
        source: 'selected_directory',
        notes: notes,
      );
    }

    final portableOutput = await _tryListArchiveFiles(
      treeUri: treeUri,
      archiveRelativePath: 'output',
    );
    if (portableOutput.isNotEmpty) {
      return ResolvedArchiveDirectory(
        archiveRelativePath: 'output',
        source: 'portable_output_child',
        notes: notes,
      );
    }

    throw const RepositoryException(
      '找不到 VerseArchiveTranslator JSON。請選取包含 archive JSON 的目錄，或選取 portable toolkit 根目錄讓 App 自動進入 output/。',
    );
  }

  Future<RepositoryLoadResult> loadWorkspace(
    WorkspaceBookmark workspace,
  ) async {
    final files = await _listArchiveFiles(
      treeUri: workspace.treeUri,
      archiveRelativePath: workspace.archiveRelativePath,
    );

    if (files.isEmpty) {
      throw const RepositoryException('目前工作目錄下找不到可載入的 archive JSON。');
    }

    final warnings = <LoadWarning>[];
    final documents = <ArchiveDocument>[];

    for (final file in files) {
      try {
        final snapshot = await _storage.readTextFile(
          treeUri: workspace.treeUri,
          relativePath: file.relativePath,
        );
        final payload = jsonDecode(snapshot.content);
        if (payload is! List) {
          warnings.add(
            LoadWarning(
              path: snapshot.relativePath,
              message: 'JSON 根節點不是 list，已略過。',
            ),
          );
          continue;
        }

        if (payload.isEmpty) {
          continue;
        }

        documents.add(
          ArchiveDocument(
            fileRelativePath: snapshot.relativePath,
            records: List<Object?>.from(payload),
            lastModified: snapshot.lastModified,
          ),
        );
      } on FormatException {
        warnings.add(
          LoadWarning(path: file.relativePath, message: 'JSON 格式錯誤，已略過。'),
        );
      } on StorageException catch (error) {
        warnings.add(
          LoadWarning(path: file.relativePath, message: error.message),
        );
      }
    }

    return RepositoryLoadResult(documents: documents, warnings: warnings);
  }

  Future<SaveTranslationResult> saveTranslation({
    required WorkspaceBookmark workspace,
    required ArchiveEntry entry,
    required String titleCn,
    required String authorCn,
    required String contentCn,
  }) async {
    final latestSnapshot = await _storage.readTextFile(
      treeUri: workspace.treeUri,
      relativePath: entry.fileRelativePath,
    );

    final latestPayload = jsonDecode(latestSnapshot.content);
    if (latestPayload is! List) {
      throw const RepositoryException('目標檔案不是 JSON list，無法保存。');
    }

    final latestRecords = List<Object?>.from(latestPayload);
    if (entry.index >= latestRecords.length) {
      throw const RepositoryException('目標 record 已不存在，請重新載入工作目錄。');
    }

    final currentRecord = asJsonMap(latestRecords[entry.index]);
    if (currentRecord == null) {
      throw const RepositoryException('目標 record 已不是 JSON object，無法保存。');
    }

    if (latestSnapshot.lastModified != entry.lastModified) {
      throw const RepositoryException('檔案在保存前已變更，請先重新載入。');
    }

    final currentSignature = buildEntrySignature(currentRecord);
    if (currentSignature != entry.signature) {
      throw const RepositoryException('record 內容在保存前已變更，請先重新載入。');
    }

    final updatedRecord = deepCopyJsonMap(currentRecord);
    final titleMap = _ensureNestedObject(updatedRecord, 'title');
    final authorMap = _ensureNestedObject(updatedRecord, 'author');
    final contentMap = _ensureNestedObject(updatedRecord, 'content');

    titleMap['cn'] = titleCn.trim();
    authorMap['cn'] = authorCn.trim();
    contentMap['cn'] = contentCn.trim();

    latestRecords[entry.index] = updatedRecord;
    final encoded = const JsonEncoder.withIndent('  ').convert(latestRecords);

    final writeResult = await _storage.writeTextFileIfUnchanged(
      treeUri: workspace.treeUri,
      relativePath: entry.fileRelativePath,
      expectedLastModified: latestSnapshot.lastModified,
      content: encoded,
    );

    final savedRecord = asJsonMap(latestRecords[entry.index]);
    if (savedRecord == null) {
      throw const RepositoryException('保存後無法解析更新後的 record。');
    }

    return SaveTranslationResult(
      updatedDocument: ArchiveDocument(
        fileRelativePath: entry.fileRelativePath,
        records: latestRecords,
        lastModified: writeResult.lastModified,
      ),
      updatedEntry: ArchiveEntry(
        fileRelativePath: entry.fileRelativePath,
        index: entry.index,
        record: savedRecord,
        lastModified: writeResult.lastModified,
      ),
    );
  }

  Future<Map<String, Object?>?> _tryReadJsonObject({
    required String treeUri,
    required String relativePath,
  }) async {
    try {
      final snapshot = await _storage.readTextFile(
        treeUri: treeUri,
        relativePath: relativePath,
      );
      final payload = jsonDecode(snapshot.content);
      if (payload is! Map) {
        return null;
      }
      return payload.map((key, value) => MapEntry(key.toString(), value));
    } catch (_) {
      return null;
    }
  }

  Future<List<DirectoryItem>> _tryListArchiveFiles({
    required String treeUri,
    required String archiveRelativePath,
  }) async {
    try {
      return await _listArchiveFiles(
        treeUri: treeUri,
        archiveRelativePath: archiveRelativePath,
      );
    } catch (_) {
      return const <DirectoryItem>[];
    }
  }

  Future<List<DirectoryItem>> _listArchiveFiles({
    required String treeUri,
    required String archiveRelativePath,
  }) async {
    final items = await _storage.listDirectory(
      treeUri: treeUri,
      relativePath: archiveRelativePath,
    );

    final jsonFiles = items
        .where((item) => item.isJsonFile)
        .toList(growable: false);
    if (jsonFiles.isEmpty) {
      return const <DirectoryItem>[];
    }

    final byName = <String, DirectoryItem>{
      for (final item in jsonFiles) item.name: item,
    };
    final standardFiles = standardArchiveFileNames
        .where(byName.containsKey)
        .map((name) => byName[name]!)
        .toList(growable: false);
    if (standardFiles.isNotEmpty) {
      return standardFiles;
    }

    final fallback = jsonFiles.toList(growable: false)
      ..sort((left, right) => left.name.compareTo(right.name));
    return fallback;
  }

  String? _extractDesktopTranslationDataDir(Map<String, Object?>? settingsMap) {
    if (settingsMap == null) {
      return null;
    }

    final translation = settingsMap['translation'];
    if (translation is! Map) {
      return null;
    }

    final value = translation['data_dir'];
    return value is String ? value.trim() : null;
  }

  Map<String, Object?> _ensureNestedObject(
    Map<String, Object?> record,
    String key,
  ) {
    final current = record[key];
    if (current is Map) {
      final mapped = current.map(
        (nestedKey, nestedValue) => MapEntry(nestedKey.toString(), nestedValue),
      );
      record[key] = mapped;
      return mapped;
    }

    final replacement = <String, Object?>{};
    record[key] = replacement;
    return replacement;
  }
}
