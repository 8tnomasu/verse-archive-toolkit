import 'package:flutter/foundation.dart';

import '../models/archive_models.dart';
import '../services/archive_repository.dart';
import '../services/preferences_store.dart';

class TranslatorController extends ChangeNotifier {
  TranslatorController({
    required ArchiveRepository repository,
    required PreferencesStore preferencesStore,
  }) : _repository = repository,
       _preferencesStore = preferencesStore;

  final ArchiveRepository _repository;
  final PreferencesStore _preferencesStore;

  TranslatorAppSettings _settings = TranslatorAppSettings.empty();
  WorkspaceBookmark? _currentWorkspace;
  ResolvedArchiveDirectory? _resolvedDirectory;
  List<ArchiveDocument> _documents = const <ArchiveDocument>[];
  List<LoadWarning> _warnings = const <LoadWarning>[];
  List<ArchiveEntry> _allEntries = const <ArchiveEntry>[];
  List<ArchiveEntry> _visibleEntries = const <ArchiveEntry>[];
  ArchiveEntry? _selectedEntry;
  EntryTypeFilter _typeFilter = EntryTypeFilter.all;
  TranslationFilter _translationFilter = TranslationFilter.all;
  String _searchQuery = '';
  String _draftTitleCn = '';
  String _draftAuthorCn = '';
  String _draftContentCn = '';
  bool _isBusy = false;
  bool _isSaving = false;
  String? _errorMessage;
  String? _infoMessage;

  TranslatorAppSettings get settings => _settings;

  WorkspaceBookmark? get currentWorkspace => _currentWorkspace;

  ResolvedArchiveDirectory? get resolvedDirectory => _resolvedDirectory;

  List<LoadWarning> get warnings => _warnings;

  List<ArchiveEntry> get visibleEntries => _visibleEntries;

  ArchiveEntry? get selectedEntry => _selectedEntry;

  EntryTypeFilter get typeFilter => _typeFilter;

  TranslationFilter get translationFilter => _translationFilter;

  String get searchQuery => _searchQuery;

  String get draftTitleCn => _draftTitleCn;

  String get draftAuthorCn => _draftAuthorCn;

  String get draftContentCn => _draftContentCn;

  bool get isBusy => _isBusy;

  bool get isSaving => _isSaving;

  String? get errorMessage => _errorMessage;

  String? get infoMessage => _infoMessage;

  bool get hasWorkspace => _currentWorkspace != null;

  bool get hasUnsavedChanges =>
      _selectedEntry != null && _computeDirtyState(_selectedEntry!);

  bool get canSave => !_isSaving && _selectedEntry != null && hasUnsavedChanges;

  ArchiveStats get stats => buildArchiveStats(_documents);

  Future<void> initialize() async {
    _settings = await _preferencesStore.load();
    final lastWorkspace = _settings.lastWorkspace;
    if (lastWorkspace != null) {
      await openWorkspace(lastWorkspace, persist: false);
    } else {
      notifyListeners();
    }
  }

  Future<bool> pickAndOpenWorkspace() async {
    _clearMessages();
    _isBusy = true;
    notifyListeners();

    try {
      final picked = await _repository.pickWorkspace();
      if (picked == null) {
        return false;
      }

      final resolved = await _repository.resolveArchiveDirectory(
        treeUri: picked.treeUri,
      );
      final workspace = WorkspaceBookmark(
        treeUri: picked.treeUri,
        displayName: picked.displayName,
        archiveRelativePath: resolved.archiveRelativePath,
        resolutionSource: resolved.source,
        lastOpenedAt: DateTime.now(),
      );

      final success = await openWorkspace(
        workspace,
        persist: true,
        resolvedDirectory: resolved,
      );
      if (success) {
        _infoMessage = '已載入 ${workspace.displayName}。';
      }
      return success;
    } finally {
      _isBusy = false;
      notifyListeners();
    }
  }

  Future<bool> openWorkspace(
    WorkspaceBookmark workspace, {
    bool persist = true,
    ResolvedArchiveDirectory? resolvedDirectory,
  }) async {
    _clearMessages();
    _isBusy = true;
    notifyListeners();

    try {
      final resolved =
          resolvedDirectory ??
          await _repository.resolveArchiveDirectory(treeUri: workspace.treeUri);
      final normalizedWorkspace = workspace.copyWith(
        archiveRelativePath: resolved.archiveRelativePath,
        resolutionSource: resolved.source,
        lastOpenedAt: DateTime.now(),
      );

      final loadResult = await _repository.loadWorkspace(normalizedWorkspace);
      _currentWorkspace = normalizedWorkspace;
      _resolvedDirectory = resolved;
      _documents = loadResult.documents;
      _warnings = loadResult.warnings;
      _allEntries = buildEntries(_documents);
      _rebuildVisibleEntries(preserveSelection: _selectedEntry);

      if (persist) {
        _settings = TranslatorAppSettings(
          recentWorkspaces: _mergeRecentWorkspace(normalizedWorkspace),
        );
        await _preferencesStore.save(_settings);
      }

      notifyListeners();
      return true;
    } catch (error) {
      _errorMessage = error.toString();
      notifyListeners();
      return false;
    } finally {
      _isBusy = false;
      notifyListeners();
    }
  }

  Future<bool> reloadWorkspace() async {
    final workspace = _currentWorkspace;
    if (workspace == null) {
      return false;
    }

    final success = await openWorkspace(workspace, persist: true);
    if (success) {
      _infoMessage = '已重新載入目前工作目錄。';
      notifyListeners();
    }
    return success;
  }

  void updateSearchQuery(String value) {
    _searchQuery = value;
    _rebuildVisibleEntries(preserveSelection: _selectedEntry);
    notifyListeners();
  }

  void updateTypeFilter(EntryTypeFilter value) {
    if (_typeFilter == value) {
      return;
    }
    _typeFilter = value;
    _rebuildVisibleEntries(preserveSelection: _selectedEntry);
    notifyListeners();
  }

  void updateTranslationFilter(TranslationFilter value) {
    if (_translationFilter == value) {
      return;
    }
    _translationFilter = value;
    notifyListeners();
  }

  void selectEntry(ArchiveEntry entry) {
    _selectedEntry = entry;
    _draftTitleCn = entry.titleCn;
    _draftAuthorCn = entry.authorCn;
    _draftContentCn = entry.contentCn;
    notifyListeners();
  }

  void selectRandomEntry() {
    final candidate = randomEntry(
      _allEntries,
      typeFilter: _typeFilter,
      translationFilter: _translationFilter,
    );
    if (candidate == null) {
      _errorMessage = '目前沒有符合條件的項目可隨機選取。';
      notifyListeners();
      return;
    }

    final existsInVisibleEntries = _visibleEntries.any(
      (entry) => _sameEntryIdentity(entry, candidate),
    );
    if (!existsInVisibleEntries) {
      _searchQuery = '';
      _rebuildVisibleEntries(preserveSelection: candidate);
    }
    selectEntry(candidate);
    _infoMessage = '已隨機選到一筆資料。';
    notifyListeners();
  }

  void updateDraftTitleCn(String value) {
    _draftTitleCn = value;
    notifyListeners();
  }

  void updateDraftAuthorCn(String value) {
    _draftAuthorCn = value;
    notifyListeners();
  }

  void updateDraftContentCn(String value) {
    _draftContentCn = value;
    notifyListeners();
  }

  Future<bool> saveCurrentEntry() async {
    final workspace = _currentWorkspace;
    final entry = _selectedEntry;
    if (workspace == null || entry == null || !hasUnsavedChanges) {
      return false;
    }

    _clearMessages();
    _isSaving = true;
    notifyListeners();

    try {
      final result = await _repository.saveTranslation(
        workspace: workspace,
        entry: entry,
        titleCn: _draftTitleCn,
        authorCn: _draftAuthorCn,
        contentCn: _draftContentCn,
      );

      _documents = _documents
          .map(
            (document) =>
                document.fileRelativePath ==
                    result.updatedDocument.fileRelativePath
                ? result.updatedDocument
                : document,
          )
          .toList(growable: false);
      _allEntries = buildEntries(_documents);
      _rebuildVisibleEntries(preserveSelection: result.updatedEntry);
      _selectedEntry = _visibleEntries.firstWhere(
        (candidate) => _sameEntryIdentity(candidate, result.updatedEntry),
        orElse: () => result.updatedEntry,
      );
      _draftTitleCn = result.updatedEntry.titleCn;
      _draftAuthorCn = result.updatedEntry.authorCn;
      _draftContentCn = result.updatedEntry.contentCn;
      _infoMessage = '譯文已保存。';

      final activeWorkspace = _currentWorkspace;
      if (activeWorkspace != null) {
        final refreshedWorkspace = activeWorkspace.copyWith(
          lastOpenedAt: DateTime.now(),
        );
        _currentWorkspace = refreshedWorkspace;
        _settings = TranslatorAppSettings(
          recentWorkspaces: _mergeRecentWorkspace(refreshedWorkspace),
        );
        await _preferencesStore.save(_settings);
      }

      notifyListeners();
      return true;
    } catch (error) {
      _errorMessage = error.toString();
      notifyListeners();
      return false;
    } finally {
      _isSaving = false;
      notifyListeners();
    }
  }

  void clearMessages() {
    _clearMessages();
    notifyListeners();
  }

  void _rebuildVisibleEntries({ArchiveEntry? preserveSelection}) {
    final previousSelection = preserveSelection ?? _selectedEntry;
    _visibleEntries = searchEntries(
      _allEntries,
      query: _searchQuery,
      typeFilter: _typeFilter,
    );

    if (_visibleEntries.isEmpty) {
      _selectedEntry = null;
      _draftTitleCn = '';
      _draftAuthorCn = '';
      _draftContentCn = '';
      return;
    }

    if (previousSelection != null) {
      for (final candidate in _visibleEntries) {
        if (_sameEntryIdentity(candidate, previousSelection)) {
          _selectedEntry = candidate;
          _draftTitleCn = candidate.titleCn;
          _draftAuthorCn = candidate.authorCn;
          _draftContentCn = candidate.contentCn;
          return;
        }
      }
    }

    final firstEntry = _visibleEntries.first;
    _selectedEntry = firstEntry;
    _draftTitleCn = firstEntry.titleCn;
    _draftAuthorCn = firstEntry.authorCn;
    _draftContentCn = firstEntry.contentCn;
  }

  List<WorkspaceBookmark> _mergeRecentWorkspace(WorkspaceBookmark workspace) {
    final merged = <WorkspaceBookmark>[
      workspace,
      ..._settings.recentWorkspaces.where(
        (item) => item.treeUri != workspace.treeUri,
      ),
    ];
    return merged.take(8).toList(growable: false);
  }

  bool _sameEntryIdentity(ArchiveEntry left, ArchiveEntry right) {
    return left.fileRelativePath == right.fileRelativePath &&
        left.index == right.index;
  }

  bool _computeDirtyState(ArchiveEntry entry) {
    return _draftTitleCn.trim() != entry.titleCn ||
        _draftAuthorCn.trim() != entry.authorCn ||
        _draftContentCn.trim() != entry.contentCn;
  }

  void _clearMessages() {
    _errorMessage = null;
    _infoMessage = null;
  }
}
