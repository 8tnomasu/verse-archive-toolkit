import 'package:flutter_test/flutter_test.dart';
import 'package:verse_archive_translator_flutter/src/models/archive_models.dart';

void main() {
  group('archive model compatibility', () {
    test('translationState ignores content.lines when content.en is empty', () {
      final record = <String, Object?>{
        'type': 'english_poem',
        'title': <String, Object?>{'en': '', 'cn': ''},
        'author': <String, Object?>{'en': '', 'cn': ''},
        'content': <String, Object?>{
          'lines': <String>['Line from lines only'],
          'en': '',
          'cn': '已有中文',
        },
      };

      expect(translationState(record), 'untranslated');
    });

    test('searchEntries matches author title content and content.lines', () {
      final entries = <ArchiveEntry>[
        ArchiveEntry(
          fileRelativePath: 'english_poems.json',
          index: 0,
          lastModified: 1,
          record: <String, Object?>{
            'type': 'english_poem',
            'title': <String, Object?>{'en': 'Night River', 'cn': ''},
            'author': <String, Object?>{'en': 'Jane Doe', 'cn': ''},
            'content': <String, Object?>{
              'lines': <String>['Line one', 'Hidden lily'],
              'en': '',
              'cn': '',
            },
          },
        ),
        ArchiveEntry(
          fileRelativePath: 'philosophy_quotes.json',
          index: 0,
          lastModified: 1,
          record: <String, Object?>{
            'type': 'philosophy',
            'title': <String, Object?>{'en': '', 'cn': ''},
            'author': <String, Object?>{'en': 'Marcus Aurelius', 'cn': ''},
            'content': <String, Object?>{
              'lines': <String>['The soul becomes dyed'],
              'en': 'The soul becomes dyed',
              'cn': '',
            },
          },
        ),
      ];

      expect(
        searchEntries(
          entries,
          query: 'lily',
          typeFilter: EntryTypeFilter.all,
        ).single.titleEn,
        'Night River',
      );
      expect(
        searchEntries(
          entries,
          query: 'marcus',
          typeFilter: EntryTypeFilter.all,
        ).single.authorEn,
        'Marcus Aurelius',
      );
      expect(
        searchEntries(entries, query: '', typeFilter: EntryTypeFilter.poems),
        hasLength(1),
      );
    });

    test('randomEntry uses translation filter semantics from desktop app', () {
      final entries = <ArchiveEntry>[
        ArchiveEntry(
          fileRelativePath: 'english_poems.json',
          index: 0,
          lastModified: 1,
          record: <String, Object?>{
            'type': 'english_poem',
            'title': <String, Object?>{'en': 'Translated', 'cn': '已翻譯'},
            'author': <String, Object?>{'en': 'Author', 'cn': '作者'},
            'content': <String, Object?>{
              'lines': <String>['Line'],
              'en': 'Line',
              'cn': '譯文',
            },
          },
        ),
        ArchiveEntry(
          fileRelativePath: 'english_poems.json',
          index: 1,
          lastModified: 1,
          record: <String, Object?>{
            'type': 'english_poem',
            'title': <String, Object?>{'en': 'Untranslated', 'cn': ''},
            'author': <String, Object?>{'en': 'Author', 'cn': ''},
            'content': <String, Object?>{
              'lines': <String>['Line'],
              'en': 'Line',
              'cn': '',
            },
          },
        ),
      ];

      final translated = randomEntry(
        entries,
        typeFilter: EntryTypeFilter.all,
        translationFilter: TranslationFilter.translated,
      );
      final untranslated = randomEntry(
        entries,
        typeFilter: EntryTypeFilter.all,
        translationFilter: TranslationFilter.untranslated,
      );

      expect(translated?.titleEn, 'Translated');
      expect(untranslated?.titleEn, 'Untranslated');
    });

    test('normalizeRelativeDirectory keeps portable child paths only', () {
      expect(normalizeRelativeDirectory('output'), 'output');
      expect(normalizeRelativeDirectory('.'), '');
      expect(normalizeRelativeDirectory(r'data\archive'), 'data/archive');
      expect(normalizeRelativeDirectory('../output'), isNull);
      expect(normalizeRelativeDirectory(r'C:\toolkit\output'), isNull);
    });
  });
}
