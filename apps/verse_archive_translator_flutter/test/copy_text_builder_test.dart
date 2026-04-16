import 'package:flutter_test/flutter_test.dart';
import 'package:verse_archive_translator_flutter/src/models/archive_models.dart';
import 'package:verse_archive_translator_flutter/src/ui/copy_text_builder.dart';

void main() {
  group('copy text builder', () {
    test('builds source copy text with title author and content.en', () {
      final entry = _buildEntry(
        titleEn: 'Night River',
        authorEn: 'Jane Doe',
        contentEn: 'One line\nTwo line',
      );

      expect(
        buildSourceCardCopyText(entry),
        '標題：Night River\n作者：Jane Doe\n\nOne line\nTwo line',
      );
    });

    test('builds translation copy text with title author and content.cn', () {
      final entry = _buildEntry(
        titleCn: '夜河',
        authorCn: '珍・杜',
        contentCn: '第一行\n第二行',
      );

      expect(buildTranslationCardCopyText(entry), '標題：夜河\n作者：珍・杜\n\n第一行\n第二行');
    });

    test('falls back to content.lines when content.en is empty', () {
      final entry = _buildEntry(
        titleEn: 'Night River',
        authorEn: 'Jane Doe',
        contentEn: '',
        contentLines: <String>['One line', 'Two line'],
      );

      expect(
        buildSourceCardCopyText(entry),
        '標題：Night River\n作者：Jane Doe\n\nOne line\nTwo line',
      );
    });

    test('returns null for empty translation content without throwing', () {
      final entry = _buildEntry();

      expect(buildTranslationCardCopyText(entry), isNull);
    });
  });
}

ArchiveEntry _buildEntry({
  String titleEn = '',
  String authorEn = '',
  String contentEn = '',
  String titleCn = '',
  String authorCn = '',
  String contentCn = '',
  List<String> contentLines = const <String>[],
}) {
  return ArchiveEntry(
    fileRelativePath: 'english_poems.json',
    index: 0,
    lastModified: 1,
    record: <String, Object?>{
      'type': 'english_poem',
      'title': <String, Object?>{'en': titleEn, 'cn': titleCn},
      'author': <String, Object?>{'en': authorEn, 'cn': authorCn},
      'content': <String, Object?>{
        'lines': contentLines,
        'en': contentEn,
        'cn': contentCn,
      },
    },
  );
}
