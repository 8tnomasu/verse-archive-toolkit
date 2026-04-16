import '../models/archive_models.dart';

String? buildSourceCardCopyText(ArchiveEntry entry) {
  return _buildCopyText(
    title: entry.titleEn,
    author: entry.authorEn,
    content: entry.contentEn,
  );
}

String? buildTranslationCardCopyText(ArchiveEntry entry) {
  return _buildCopyText(
    title: entry.titleCn,
    author: entry.authorCn,
    content: entry.contentCn,
  );
}

String? _buildCopyText({
  required String title,
  required String author,
  required String content,
}) {
  final cleanTitle = title.trim();
  final cleanAuthor = author.trim();
  final cleanContent = content.trim();

  if (cleanTitle.isEmpty && cleanAuthor.isEmpty && cleanContent.isEmpty) {
    return null;
  }

  return '標題：$cleanTitle\n作者：$cleanAuthor\n\n$cleanContent';
}
