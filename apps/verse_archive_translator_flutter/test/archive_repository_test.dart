import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:verse_archive_translator_flutter/src/models/archive_models.dart';
import 'package:verse_archive_translator_flutter/src/services/archive_repository.dart';

import 'test_support.dart';

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

    test('skips empty json lists like desktop repository', () async {
      final storage = FakeWorkspaceStorage(
        files: <String, String>{
          'english_poems.json': '[]',
          'philosophy_quotes.json': jsonEncode(<Object?>[
            <String, Object?>{
              'type': 'philosophy',
              'title': <String, Object?>{'en': '', 'cn': ''},
              'author': <String, Object?>{'en': 'Author', 'cn': ''},
              'content': <String, Object?>{
                'lines': <String>['Quote'],
                'en': 'Quote',
                'cn': '',
              },
            },
          ]),
        },
      );

      final repository = ArchiveRepository(storage);
      final result = await repository.loadWorkspace(sampleWorkspaceBookmark());

      expect(result.documents, hasLength(1));
      expect(
        result.documents.single.fileRelativePath,
        'philosophy_quotes.json',
      );
    });

    test('save only updates cn fields and preserves review metadata', () async {
      final storage = FakeWorkspaceStorage(
        files: <String, String>{
          'english_poems_review.json': jsonEncode(<Object?>[
            <String, Object?>{
              'type': 'english_poem',
              'reason': 'manual_review',
              'filter_detail': 'line_count',
              'source_tag': 'batch-01',
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
      final workspace = sampleWorkspaceBookmark();
      final loadResult = await repository.loadWorkspace(workspace);
      final entry = buildEntries(loadResult.documents).single;

      final saveResult = await repository.saveTranslation(
        workspace: workspace,
        entry: entry,
        titleCn: 'Night River CN',
        authorCn: 'Jane Doe CN',
        contentCn: 'Line one cn\nLine two cn',
      );

      final savedJson =
          jsonDecode(storage.files['english_poems_review.json']!)
              as List<Object?>;
      final savedRecord = savedJson.single as Map<Object?, Object?>;
      final savedTitle = savedRecord['title'] as Map<Object?, Object?>;
      final savedAuthor = savedRecord['author'] as Map<Object?, Object?>;
      final savedContent = savedRecord['content'] as Map<Object?, Object?>;

      expect(savedTitle['en'], 'Night River');
      expect(savedTitle['cn'], 'Night River CN');
      expect(savedAuthor['en'], 'Jane Doe');
      expect(savedAuthor['cn'], 'Jane Doe CN');
      expect(savedContent['en'], 'One line\nTwo line');
      expect(savedContent['lines'], <String>['One line', 'Two line']);
      expect(savedContent['cn'], 'Line one cn\nLine two cn');
      expect(savedRecord['reason'], 'manual_review');
      expect(savedRecord['filter_detail'], 'line_count');
      expect(savedRecord['source_tag'], 'batch-01');
      expect(saveResult.updatedEntry.record['reason'], 'manual_review');
    });

    test('rejects save when file mtime changed before save', () async {
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
      final workspace = sampleWorkspaceBookmark();
      final loadResult = await repository.loadWorkspace(workspace);
      final entry = buildEntries(loadResult.documents).single;

      storage.replaceFile(
        'english_poems.json',
        jsonEncode(<Object?>[
          <String, Object?>{
            'type': 'english_poem',
            'title': <String, Object?>{'en': 'Night River', 'cn': ''},
            'author': <String, Object?>{'en': 'Jane Doe', 'cn': ''},
            'content': <String, Object?>{
              'lines': <String>['Changed line'],
              'en': 'Changed line',
              'cn': '',
            },
          },
        ]),
      );

      expect(
        () => repository.saveTranslation(
          workspace: workspace,
          entry: entry,
          titleCn: 'Night River CN',
          authorCn: 'Jane Doe CN',
          contentCn: 'Line one cn\nLine two cn',
        ),
        throwsA(isA<RepositoryException>()),
      );
    });

    test(
      'rejects save when signature changed even if mtime did not bump',
      () async {
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
        final workspace = sampleWorkspaceBookmark();
        final loadResult = await repository.loadWorkspace(workspace);
        final entry = buildEntries(loadResult.documents).single;

        storage.replaceFile(
          'english_poems.json',
          jsonEncode(<Object?>[
            <String, Object?>{
              'type': 'english_poem',
              'title': <String, Object?>{'en': 'Night River Updated', 'cn': ''},
              'author': <String, Object?>{'en': 'Jane Doe', 'cn': ''},
              'content': <String, Object?>{
                'lines': <String>['One line', 'Two line'],
                'en': 'One line\nTwo line',
                'cn': '',
              },
            },
          ]),
          bumpLastModified: false,
        );

        expect(
          () => repository.saveTranslation(
            workspace: workspace,
            entry: entry,
            titleCn: 'Night River CN',
            authorCn: 'Jane Doe CN',
            contentCn: 'Line one cn\nLine two cn',
          ),
          throwsA(isA<RepositoryException>()),
        );
      },
    );
  });
}
