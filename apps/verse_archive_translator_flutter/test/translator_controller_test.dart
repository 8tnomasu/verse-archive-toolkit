import 'package:flutter_test/flutter_test.dart';
import 'package:verse_archive_translator_flutter/src/controllers/translator_controller.dart';
import 'package:verse_archive_translator_flutter/src/models/archive_models.dart';
import 'package:verse_archive_translator_flutter/src/services/archive_repository.dart';
import 'package:verse_archive_translator_flutter/src/services/preferences_store.dart';

import 'test_support.dart';

void main() {
  group('TranslatorController', () {
    test(
      'initialize restores last workspace bookmark and loads entries',
      () async {
        final workspace = sampleWorkspaceBookmark(
          archiveRelativePath: 'output',
        );
        final repository = TestArchiveRepository(
          resolvedDirectory: const ResolvedArchiveDirectory(
            archiveRelativePath: 'output',
            source: 'desktop_settings',
            notes: <String>[],
          ),
          loadResult: RepositoryLoadResult(
            documents: <ArchiveDocument>[
              ArchiveDocument(
                fileRelativePath: 'output/english_poems.json',
                lastModified: 1,
                records: <Object?>[
                  <String, Object?>{
                    'type': 'english_poem',
                    'title': <String, Object?>{'en': 'Night River', 'cn': ''},
                    'author': <String, Object?>{'en': 'Jane Doe', 'cn': ''},
                    'content': <String, Object?>{
                      'lines': <String>['Line one', 'Line two'],
                      'en': 'Line one\nLine two',
                      'cn': '',
                    },
                  },
                ],
              ),
            ],
            warnings: const <LoadWarning>[],
          ),
        );
        final preferences = MemoryPreferencesStore(
          TranslatorAppSettings(
            recentWorkspaces: <WorkspaceBookmark>[workspace],
          ),
        );
        final controller = TranslatorController(
          repository: repository,
          preferencesStore: preferences,
        );

        await controller.initialize();

        expect(controller.currentWorkspace?.treeUri, workspace.treeUri);
        expect(controller.currentWorkspace?.archiveRelativePath, 'output');
        expect(controller.visibleEntries, hasLength(1));
        expect(repository.loadedWorkspaces.single.treeUri, workspace.treeUri);
      },
    );

    test(
      'translation filter only affects random pick, not visible list',
      () async {
        final repository = TestArchiveRepository(
          resolvedDirectory: const ResolvedArchiveDirectory(
            archiveRelativePath: '',
            source: 'selected_directory',
            notes: <String>[],
          ),
          loadResult: RepositoryLoadResult(
            documents: <ArchiveDocument>[
              ArchiveDocument(
                fileRelativePath: 'english_poems.json',
                lastModified: 1,
                records: <Object?>[
                  <String, Object?>{
                    'type': 'english_poem',
                    'title': <String, Object?>{'en': 'Translated', 'cn': '已翻譯'},
                    'author': <String, Object?>{'en': 'Author', 'cn': '作者'},
                    'content': <String, Object?>{
                      'lines': <String>['Line'],
                      'en': 'Line',
                      'cn': '譯文',
                    },
                  },
                  <String, Object?>{
                    'type': 'english_poem',
                    'title': <String, Object?>{'en': 'Untranslated', 'cn': ''},
                    'author': <String, Object?>{'en': 'Author', 'cn': ''},
                    'content': <String, Object?>{
                      'lines': <String>['Line'],
                      'en': 'Line',
                      'cn': '',
                    },
                  },
                ],
              ),
            ],
            warnings: const <LoadWarning>[],
          ),
        );
        final controller = TranslatorController(
          repository: repository,
          preferencesStore: MemoryPreferencesStore(
            TranslatorAppSettings.empty(),
          ),
        );

        await controller.openWorkspace(sampleWorkspaceBookmark());
        expect(controller.visibleEntries, hasLength(2));

        controller.updateTranslationFilter(TranslationFilter.untranslated);
        expect(controller.visibleEntries, hasLength(2));

        controller.selectRandomEntry();
        expect(controller.selectedEntry?.titleEn, 'Untranslated');
      },
    );

    test('dirty state tracks draft changes and clears after save', () async {
      final repository = TestArchiveRepository(
        resolvedDirectory: const ResolvedArchiveDirectory(
          archiveRelativePath: '',
          source: 'selected_directory',
          notes: <String>[],
        ),
        loadResult: RepositoryLoadResult(
          documents: <ArchiveDocument>[
            ArchiveDocument(
              fileRelativePath: 'english_poems.json',
              lastModified: 1,
              records: <Object?>[
                <String, Object?>{
                  'type': 'english_poem',
                  'title': <String, Object?>{'en': 'Night River', 'cn': ''},
                  'author': <String, Object?>{'en': 'Jane Doe', 'cn': ''},
                  'content': <String, Object?>{
                    'lines': <String>['Line one', 'Line two'],
                    'en': 'Line one\nLine two',
                    'cn': '',
                  },
                },
              ],
            ),
          ],
          warnings: const <LoadWarning>[],
        ),
      );
      final controller = TranslatorController(
        repository: repository,
        preferencesStore: MemoryPreferencesStore(TranslatorAppSettings.empty()),
      );

      await controller.openWorkspace(sampleWorkspaceBookmark());
      expect(controller.hasUnsavedChanges, isFalse);

      controller.updateDraftContentCn('新的譯文');
      expect(controller.hasUnsavedChanges, isTrue);

      final saved = await controller.saveCurrentEntry();
      expect(saved, isTrue);
      expect(controller.hasUnsavedChanges, isFalse);
      expect(controller.selectedEntry?.contentCn, '新的譯文');
    });
  });
}

class MemoryPreferencesStore extends PreferencesStore {
  MemoryPreferencesStore(this._settings);

  TranslatorAppSettings _settings;

  @override
  Future<TranslatorAppSettings> load() async => _settings;

  @override
  Future<void> save(TranslatorAppSettings settings) async {
    _settings = settings;
  }
}

class TestArchiveRepository extends ArchiveRepository {
  TestArchiveRepository({
    required this.resolvedDirectory,
    required this.loadResult,
  }) : super(FakeWorkspaceStorage(files: const <String, String>{}));

  final ResolvedArchiveDirectory resolvedDirectory;
  RepositoryLoadResult loadResult;
  final List<WorkspaceBookmark> loadedWorkspaces = <WorkspaceBookmark>[];

  @override
  Future<ResolvedArchiveDirectory> resolveArchiveDirectory({
    required String treeUri,
  }) async {
    return resolvedDirectory;
  }

  @override
  Future<RepositoryLoadResult> loadWorkspace(
    WorkspaceBookmark workspace,
  ) async {
    loadedWorkspaces.add(workspace);
    return loadResult;
  }

  @override
  Future<SaveTranslationResult> saveTranslation({
    required WorkspaceBookmark workspace,
    required ArchiveEntry entry,
    required String titleCn,
    required String authorCn,
    required String contentCn,
  }) async {
    final updatedRecord = deepCopyJsonMap(entry.record);
    (updatedRecord['title'] as Map<String, Object?>)['cn'] = titleCn.trim();
    (updatedRecord['author'] as Map<String, Object?>)['cn'] = authorCn.trim();
    (updatedRecord['content'] as Map<String, Object?>)['cn'] = contentCn.trim();

    final updatedDocument = ArchiveDocument(
      fileRelativePath: entry.fileRelativePath,
      lastModified: entry.lastModified + 1,
      records: <Object?>[updatedRecord],
    );
    loadResult = RepositoryLoadResult(
      documents: <ArchiveDocument>[updatedDocument],
      warnings: loadResult.warnings,
    );

    return SaveTranslationResult(
      updatedDocument: updatedDocument,
      updatedEntry: ArchiveEntry(
        fileRelativePath: entry.fileRelativePath,
        index: entry.index,
        record: updatedRecord,
        lastModified: updatedDocument.lastModified,
      ),
    );
  }
}
