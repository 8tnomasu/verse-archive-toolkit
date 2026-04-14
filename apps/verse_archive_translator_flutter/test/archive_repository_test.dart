import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:verse_archive_translator_flutter/src/models/archive_models.dart';
import 'package:verse_archive_translator_flutter/src/services/archive_repository.dart';
import 'package:verse_archive_translator_flutter/src/storage/workspace_storage.dart';

void main() {
  group('ArchiveRepository', () {
    test('resolves archive directory from desktop settings json', () async {
      final storage = FakeWorkspaceStorage(
        files: <String, String>{
          'data/settings.json': jsonEncode(<String, Object?>{
            'translation': <String, Object?>{'data_dir': 'output'},
          }),
          'output/english_poems.json': '[]',
        },
      );

      final repository = ArchiveRepository(storage);
      final resolved = await repository.resolveArchiveDirectory(
        treeUri: 'workspace',
      );

      expect(resolved.archiveRelativePath, 'output');
      expect(resolved.source, 'desktop_settings');
    });

    test('saves translation without touching content lines', () async {
      final storage = FakeWorkspaceStorage(
        files: <String, String>{
          'english_poems.json': jsonEncode(<Object?>[
            <String, Object?>{
              'type': 'english_poem',
              'title': <String, Object?>{'en': 'Night River', 'cn': ''},
              'author': <String, Object?>{'en': 'Jane Doe', 'cn': ''},
              'content': <String, Object?>{
                'lines': <String>['One line', 'Two line'],
                'en': 'One line\nTwo line',
                'cn': '',
              },
            },
          ]),
        },
      );

      final repository = ArchiveRepository(storage);
      final workspace = WorkspaceBookmark(
        treeUri: 'workspace',
        displayName: 'Workspace',
        archiveRelativePath: '',
        resolutionSource: 'selected_directory',
        lastOpenedAt: DateTime.now(),
      );

      final loadResult = await repository.loadWorkspace(workspace);
      final entry = buildEntries(loadResult.documents).single;

      final saveResult = await repository.saveTranslation(
        workspace: workspace,
        entry: entry,
        titleCn: 'Night River CN',
        authorCn: 'Jane Doe CN',
        contentCn: 'Line one cn\nLine two cn',
      );

      final content =
          saveResult.updatedEntry.record['content'] as Map<Object?, Object?>;
      expect(content['lines'], <String>['One line', 'Two line']);
      expect(content['cn'], 'Line one cn\nLine two cn');

      final savedJson =
          jsonDecode(storage.files['english_poems.json']!) as List<Object?>;
      final savedRecord = savedJson.single as Map<Object?, Object?>;
      final savedContent = savedRecord['content'] as Map<Object?, Object?>;
      expect(savedContent['lines'], <String>['One line', 'Two line']);
      expect(savedContent['cn'], 'Line one cn\nLine two cn');
    });
  });
}

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

  String _normalize(String rawPath) {
    return rawPath.replaceAll('\\', '/').trim();
  }
}

class _ChildEntry {
  const _ChildEntry({required this.relativePath, required this.isDirectory});

  final String relativePath;
  final bool isDirectory;
}
