import 'dart:convert';
import 'dart:math';

const List<String> standardArchiveFileNames = <String>[
  'english_poems.json',
  'english_poems_review.json',
  'philosophy_quotes.json',
  'philosophy_quotes_review.json',
];

enum EntryTypeFilter { all, poems, quotes }

enum TranslationFilter { all, untranslated, partial, translated }

class DirectoryItem {
  const DirectoryItem({
    required this.name,
    required this.relativePath,
    required this.isDirectory,
    required this.lastModified,
    required this.size,
  });

  factory DirectoryItem.fromMap(Map<Object?, Object?> map) {
    return DirectoryItem(
      name: map.stringValue('name'),
      relativePath: map.stringValue('relativePath'),
      isDirectory: map.boolValue('isDirectory'),
      lastModified: map.intValue('lastModified'),
      size: map.optionalIntValue('size'),
    );
  }

  final String name;
  final String relativePath;
  final bool isDirectory;
  final int lastModified;
  final int? size;

  bool get isJsonFile => !isDirectory && name.toLowerCase().endsWith('.json');
}

class ArchiveDocument {
  const ArchiveDocument({
    required this.fileRelativePath,
    required this.records,
    required this.lastModified,
  });

  final String fileRelativePath;
  final List<Object?> records;
  final int lastModified;

  String get fileName => basenameOfRelativePath(fileRelativePath);
}

class ArchiveEntry {
  const ArchiveEntry({
    required this.fileRelativePath,
    required this.index,
    required this.record,
    required this.lastModified,
  });

  final String fileRelativePath;
  final int index;
  final Map<String, Object?> record;
  final int lastModified;

  String get fileName => basenameOfRelativePath(fileRelativePath);

  String get typeLabel => nestedString(record, 'type').trim();

  String get authorEn => nestedString(record, 'author', 'en').trim();

  String get titleEn => nestedString(record, 'title', 'en').trim();

  String get titleCn => nestedString(record, 'title', 'cn').trim();

  String get authorCn => nestedString(record, 'author', 'cn').trim();

  String get contentCn => nestedString(record, 'content', 'cn').trim();

  String get contentEn {
    final content = nestedString(record, 'content', 'en').trim();
    if (content.isNotEmpty) {
      return content;
    }
    return recordLines(record).join('\n');
  }

  String get signature => buildEntrySignature(record);

  String get summary {
    final text = contentEn.replaceAll('\n', ' ').trim();
    if (text.length <= 80) {
      return text;
    }
    return '${text.substring(0, 80)}...';
  }
}

class ArchiveStats {
  const ArchiveStats({
    required this.total,
    required this.translated,
    required this.partial,
    required this.untranslated,
  });

  final int total;
  final int translated;
  final int partial;
  final int untranslated;
}

class LoadWarning {
  const LoadWarning({required this.path, required this.message});

  final String path;
  final String message;
}

class RepositoryLoadResult {
  const RepositoryLoadResult({required this.documents, required this.warnings});

  final List<ArchiveDocument> documents;
  final List<LoadWarning> warnings;
}

class ResolvedArchiveDirectory {
  const ResolvedArchiveDirectory({
    required this.archiveRelativePath,
    required this.source,
    required this.notes,
    this.desktopSettingValue,
  });

  final String archiveRelativePath;
  final String source;
  final List<String> notes;
  final String? desktopSettingValue;
}

class WorkspaceBookmark {
  const WorkspaceBookmark({
    required this.treeUri,
    required this.displayName,
    required this.archiveRelativePath,
    required this.resolutionSource,
    required this.lastOpenedAt,
  });

  factory WorkspaceBookmark.fromJson(Map<String, Object?> json) {
    return WorkspaceBookmark(
      treeUri: nestedString(json, 'treeUri'),
      displayName: nestedString(json, 'displayName'),
      archiveRelativePath: nestedString(json, 'archiveRelativePath'),
      resolutionSource: nestedString(json, 'resolutionSource'),
      lastOpenedAt:
          DateTime.tryParse(nestedString(json, 'lastOpenedAt')) ??
          DateTime.fromMillisecondsSinceEpoch(0),
    );
  }

  final String treeUri;
  final String displayName;
  final String archiveRelativePath;
  final String resolutionSource;
  final DateTime lastOpenedAt;

  WorkspaceBookmark copyWith({
    String? treeUri,
    String? displayName,
    String? archiveRelativePath,
    String? resolutionSource,
    DateTime? lastOpenedAt,
  }) {
    return WorkspaceBookmark(
      treeUri: treeUri ?? this.treeUri,
      displayName: displayName ?? this.displayName,
      archiveRelativePath: archiveRelativePath ?? this.archiveRelativePath,
      resolutionSource: resolutionSource ?? this.resolutionSource,
      lastOpenedAt: lastOpenedAt ?? this.lastOpenedAt,
    );
  }

  Map<String, Object?> toJson() {
    return <String, Object?>{
      'treeUri': treeUri,
      'displayName': displayName,
      'archiveRelativePath': archiveRelativePath,
      'resolutionSource': resolutionSource,
      'lastOpenedAt': lastOpenedAt.toIso8601String(),
    };
  }
}

class TranslatorAppSettings {
  const TranslatorAppSettings({required this.recentWorkspaces});

  factory TranslatorAppSettings.empty() {
    return const TranslatorAppSettings(recentWorkspaces: <WorkspaceBookmark>[]);
  }

  factory TranslatorAppSettings.fromJson(Map<String, Object?> json) {
    final rawList = json['recentWorkspaces'];
    if (rawList is! List) {
      return TranslatorAppSettings.empty();
    }

    return TranslatorAppSettings(
      recentWorkspaces: rawList
          .whereType<Map>()
          .map(
            (item) => WorkspaceBookmark.fromJson(
              item.map((key, value) => MapEntry(key.toString(), value)),
            ),
          )
          .toList(growable: false),
    );
  }

  final List<WorkspaceBookmark> recentWorkspaces;

  WorkspaceBookmark? get lastWorkspace =>
      recentWorkspaces.isEmpty ? null : recentWorkspaces.first;

  Map<String, Object?> toJson() {
    return <String, Object?>{
      'recentWorkspaces': recentWorkspaces
          .map((item) => item.toJson())
          .toList(growable: false),
    };
  }
}

String nestedString(
  Map<String, Object?> item,
  String key, [
  String? nestedKey,
]) {
  if (nestedKey == null) {
    final value = item[key];
    return value is String ? value : '';
  }

  final nested = item[key];
  if (nested is! Map) {
    return '';
  }

  final value = nested[nestedKey];
  return value is String ? value : '';
}

List<String> recordLines(Map<String, Object?> item) {
  final content = item['content'];
  if (content is! Map) {
    return const <String>[];
  }

  final lines = content['lines'];
  if (lines is! List) {
    return const <String>[];
  }

  return lines
      .map((line) => line.toString().trim())
      .where((line) => line.isNotEmpty)
      .toList(growable: false);
}

String buildEntrySignature(Map<String, Object?> record) {
  final contentEn = nestedString(record, 'content', 'en').trim();

  return <String>[
    nestedString(record, 'type').trim(),
    nestedString(record, 'author', 'en').trim(),
    nestedString(record, 'title', 'en').trim(),
    contentEn.isNotEmpty ? contentEn : recordLines(record).join('\n'),
  ].join('|||');
}

String translationState(Map<String, Object?> record) {
  final titleEn = nestedString(record, 'title', 'en').trim();
  final authorEn = nestedString(record, 'author', 'en').trim();
  final contentEn = nestedString(record, 'content', 'en').trim();

  final titleCn = nestedString(record, 'title', 'cn').trim();
  final authorCn = nestedString(record, 'author', 'cn').trim();
  final contentCn = nestedString(record, 'content', 'cn').trim();

  final requiredFields = <MapEntry<String, String>>[];
  if (titleEn.isNotEmpty) {
    requiredFields.add(MapEntry(titleEn, titleCn));
  }
  if (authorEn.isNotEmpty) {
    requiredFields.add(MapEntry(authorEn, authorCn));
  }
  if (contentEn.isNotEmpty) {
    requiredFields.add(MapEntry(contentEn, contentCn));
  }

  if (requiredFields.isEmpty) {
    return 'untranslated';
  }

  final translatedCount = requiredFields
      .where((field) => field.value.trim().isNotEmpty)
      .length;
  if (translatedCount == 0) {
    return 'untranslated';
  }
  if (translatedCount == requiredFields.length) {
    return 'translated';
  }
  return 'partial';
}

ArchiveStats buildArchiveStats(List<ArchiveDocument> documents) {
  var translated = 0;
  var partial = 0;
  var untranslated = 0;
  var total = 0;

  for (final document in documents) {
    for (final record in document.records) {
      final map = asJsonMap(record);
      if (map == null) {
        continue;
      }

      total += 1;
      final state = translationState(map);
      if (state == 'translated') {
        translated += 1;
      } else if (state == 'partial') {
        partial += 1;
      } else {
        untranslated += 1;
      }
    }
  }

  return ArchiveStats(
    total: total,
    translated: translated,
    partial: partial,
    untranslated: untranslated,
  );
}

List<ArchiveEntry> buildEntries(List<ArchiveDocument> documents) {
  final entries = <ArchiveEntry>[];

  for (final document in documents) {
    for (var index = 0; index < document.records.length; index += 1) {
      final map = asJsonMap(document.records[index]);
      if (map == null) {
        continue;
      }

      entries.add(
        ArchiveEntry(
          fileRelativePath: document.fileRelativePath,
          index: index,
          record: map,
          lastModified: document.lastModified,
        ),
      );
    }
  }

  return entries;
}

List<ArchiveEntry> filterEntries(
  List<ArchiveEntry> entries, {
  required String query,
  required EntryTypeFilter typeFilter,
  required TranslationFilter translationFilter,
}) {
  final normalizedQuery = query.trim().toLowerCase();

  return entries
      .where((entry) {
        if (typeFilter == EntryTypeFilter.poems &&
            entry.typeLabel != 'english_poem') {
          return false;
        }
        if (typeFilter == EntryTypeFilter.quotes &&
            entry.typeLabel != 'philosophy') {
          return false;
        }

        final state = translationState(entry.record);
        if (translationFilter != TranslationFilter.all &&
            state != translationFilter.name) {
          return false;
        }

        if (normalizedQuery.isEmpty) {
          return true;
        }

        final joined = <String>[
          entry.authorEn,
          entry.titleEn,
          entry.contentEn,
          recordLines(entry.record).join('\n'),
        ].where((part) => part.isNotEmpty).join('\n').toLowerCase();

        return joined.contains(normalizedQuery);
      })
      .toList(growable: false);
}

ArchiveEntry? randomEntry(
  List<ArchiveEntry> entries, {
  required EntryTypeFilter typeFilter,
  required TranslationFilter translationFilter,
  Random? random,
}) {
  final filtered = filterEntries(
    entries,
    query: '',
    typeFilter: typeFilter,
    translationFilter: translationFilter,
  );

  if (filtered.isEmpty) {
    return null;
  }

  final generator = random ?? Random();
  return filtered[generator.nextInt(filtered.length)];
}

Map<String, Object?>? asJsonMap(Object? value) {
  if (value is! Map) {
    return null;
  }

  return value.map((key, value) => MapEntry(key.toString(), value));
}

Map<String, Object?> deepCopyJsonMap(Map<String, Object?> source) {
  final decoded = jsonDecode(jsonEncode(source));
  if (decoded is! Map) {
    return <String, Object?>{};
  }
  return decoded.map((key, value) => MapEntry(key.toString(), value));
}

String basenameOfRelativePath(String relativePath) {
  final normalized = relativePath.replaceAll('\\', '/');
  final segments = normalized
      .split('/')
      .where((segment) => segment.isNotEmpty)
      .toList(growable: false);
  if (segments.isEmpty) {
    return normalized;
  }
  return segments.last;
}

String joinRelativePath(String base, String name) {
  final cleanBase = base.replaceAll('\\', '/').trim();
  final cleanName = name.replaceAll('\\', '/').trim();
  if (cleanBase.isEmpty) {
    return cleanName;
  }
  if (cleanName.isEmpty) {
    return cleanBase;
  }
  return '$cleanBase/$cleanName';
}

String? normalizeRelativeDirectory(String rawPath) {
  final normalized = rawPath.replaceAll('\\', '/').trim();
  if (normalized.isEmpty || normalized == '.') {
    return '';
  }
  if (normalized.startsWith('/')) {
    return null;
  }
  if (RegExp(r'^[A-Za-z]:').hasMatch(normalized)) {
    return null;
  }

  final segments = <String>[];
  for (final segment in normalized.split('/')) {
    final cleanSegment = segment.trim();
    if (cleanSegment.isEmpty || cleanSegment == '.') {
      continue;
    }
    if (cleanSegment == '..') {
      return null;
    }
    segments.add(cleanSegment);
  }

  return segments.join('/');
}

extension on Map<Object?, Object?> {
  String stringValue(String key) {
    final value = this[key];
    return value is String ? value : '';
  }

  bool boolValue(String key) {
    final value = this[key];
    return value is bool ? value : false;
  }

  int intValue(String key) {
    final value = this[key];
    if (value is int) {
      return value;
    }
    if (value is num) {
      return value.toInt();
    }
    return 0;
  }

  int? optionalIntValue(String key) {
    final value = this[key];
    if (value is int) {
      return value;
    }
    if (value is num) {
      return value.toInt();
    }
    return null;
  }
}
