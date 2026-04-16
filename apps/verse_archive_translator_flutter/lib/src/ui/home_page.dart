import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../controllers/translator_controller.dart';
import '../models/archive_models.dart';
import 'copy_text_builder.dart';

const Map<String, String> _typeLabels = <String, String>{
  'english_poem': '英文詩',
  'philosophy': '哲學語錄',
};

const Map<String, String> _translationLabels = <String, String>{
  'translated': '已完成',
  'partial': '部分',
  'untranslated': '未翻譯',
};

const Map<String, String> _resolutionSourceLabels = <String, String>{
  'desktop_settings': '依 data/settings.json 解析',
  'selected_directory': '直接使用所選目錄',
  'portable_output_child': '自動切到 portable output/',
};

class TranslatorHomePage extends StatefulWidget {
  const TranslatorHomePage({required this.controller, super.key});

  final TranslatorController controller;

  @override
  State<TranslatorHomePage> createState() => _TranslatorHomePageState();
}

class _TranslatorHomePageState extends State<TranslatorHomePage> {
  late final TextEditingController _searchController = TextEditingController(
    text: widget.controller.searchQuery,
  );
  late final TextEditingController _titleController = TextEditingController();
  late final TextEditingController _authorController = TextEditingController();
  late final TextEditingController _contentController = TextEditingController();
  final ScrollController _editorScrollController = ScrollController();
  final GlobalKey _titleFieldKey = GlobalKey();
  final GlobalKey _authorFieldKey = GlobalKey();
  final GlobalKey _contentFieldKey = GlobalKey();
  final FocusNode _titleFocusNode = FocusNode();
  final FocusNode _authorFocusNode = FocusNode();
  final FocusNode _contentFocusNode = FocusNode();
  int _mobilePaneIndex = 0;

  @override
  void initState() {
    super.initState();
    _bindEnsureVisible(_titleFocusNode, _titleFieldKey);
    _bindEnsureVisible(_authorFocusNode, _authorFieldKey);
    _bindEnsureVisible(_contentFocusNode, _contentFieldKey);
  }

  @override
  void dispose() {
    _searchController.dispose();
    _titleController.dispose();
    _authorController.dispose();
    _contentController.dispose();
    _editorScrollController.dispose();
    _titleFocusNode.dispose();
    _authorFocusNode.dispose();
    _contentFocusNode.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: widget.controller,
      builder: (context, _) {
        _syncControllerValues();

        final mediaQuery = MediaQuery.of(context);
        final isWideLayout = mediaQuery.size.width >= 960;
        final keyboardVisible = mediaQuery.viewInsets.bottom > 0;

        return PopScope(
          canPop: !widget.controller.hasUnsavedChanges,
          onPopInvokedWithResult: (didPop, _) async {
            if (didPop || !mounted || !widget.controller.hasUnsavedChanges) {
              return;
            }
            final shouldClose = await _confirmDiscardChanges();
            if (shouldClose && context.mounted) {
              Navigator.of(context).pop();
            }
          },
          child: Scaffold(
            resizeToAvoidBottomInset: true,
            appBar: AppBar(
              title: Text(
                _buildAppBarTitle(),
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
              actions: [
                IconButton(
                  tooltip: '選擇資料夾',
                  onPressed: widget.controller.isBusy ? null : _pickWorkspace,
                  icon: const Icon(Icons.folder_open),
                ),
                IconButton(
                  tooltip: '最近使用',
                  onPressed:
                      widget.controller.settings.recentWorkspaces.isNotEmpty
                      ? _showRecentWorkspacesSheet
                      : null,
                  icon: const Icon(Icons.history),
                ),
                IconButton(
                  tooltip: '工作區資訊',
                  onPressed: widget.controller.hasWorkspace
                      ? _showWorkspaceInfoSheet
                      : null,
                  icon: const Icon(Icons.info_outline),
                ),
                IconButton(
                  tooltip: '重新載入',
                  onPressed:
                      widget.controller.hasWorkspace &&
                          !widget.controller.isBusy
                      ? _reloadWorkspace
                      : null,
                  icon: const Icon(Icons.refresh),
                ),
                IconButton(
                  tooltip: '保存',
                  onPressed: widget.controller.canSave
                      ? _saveCurrentEntry
                      : null,
                  icon: const Icon(Icons.save_outlined),
                ),
              ],
            ),
            bottomNavigationBar: isWideLayout || !widget.controller.hasWorkspace
                ? null
                : keyboardVisible
                ? null
                : SafeArea(
                    top: false,
                    child: NavigationBar(
                      selectedIndex: _mobilePaneIndex,
                      onDestinationSelected: (index) {
                        setState(() {
                          _mobilePaneIndex = index;
                        });
                      },
                      destinations: const [
                        NavigationDestination(
                          icon: Icon(Icons.list_alt_outlined),
                          selectedIcon: Icon(Icons.list_alt),
                          label: '列表',
                        ),
                        NavigationDestination(
                          icon: Icon(Icons.edit_note_outlined),
                          selectedIcon: Icon(Icons.edit_note),
                          label: '編修',
                        ),
                      ],
                    ),
                  ),
            body: SafeArea(
              child: Column(
                children: [
                  if (widget.controller.isBusy || widget.controller.isSaving)
                    const LinearProgressIndicator(minHeight: 2),
                  if (widget.controller.errorMessage != null ||
                      widget.controller.infoMessage != null ||
                      widget.controller.warnings.isNotEmpty)
                    Padding(
                      padding: const EdgeInsets.fromLTRB(12, 12, 12, 0),
                      child: _buildMessages(context),
                    ),
                  Expanded(
                    child: Padding(
                      padding: const EdgeInsets.all(12),
                      child: widget.controller.hasWorkspace
                          ? isWideLayout
                                ? Row(
                                    crossAxisAlignment:
                                        CrossAxisAlignment.start,
                                    children: [
                                      SizedBox(
                                        width: 380,
                                        child: _buildListPane(context),
                                      ),
                                      const SizedBox(width: 12),
                                      Expanded(
                                        child: _buildEditorPane(
                                          context,
                                          keyboardVisible: keyboardVisible,
                                        ),
                                      ),
                                    ],
                                  )
                                : IndexedStack(
                                    index: _mobilePaneIndex,
                                    children: [
                                      _buildListPane(context),
                                      _buildEditorPane(
                                        context,
                                        keyboardVisible: keyboardVisible,
                                      ),
                                    ],
                                  )
                          : _buildEmptyState(context),
                    ),
                  ),
                ],
              ),
            ),
          ),
        );
      },
    );
  }

  void _bindEnsureVisible(FocusNode focusNode, GlobalKey fieldKey) {
    focusNode.addListener(() {
      if (!focusNode.hasFocus) {
        return;
      }

      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (!mounted) {
          return;
        }
        final fieldContext = fieldKey.currentContext;
        if (fieldContext == null) {
          return;
        }
        Scrollable.ensureVisible(
          fieldContext,
          alignment: 0.18,
          duration: const Duration(milliseconds: 220),
          curve: Curves.easeOutCubic,
        );
      });
    });
  }

  String _buildAppBarTitle() {
    final workspace = widget.controller.currentWorkspace;
    final dirty = widget.controller.hasUnsavedChanges ? ' *' : '';
    if (workspace == null) {
      return 'VerseArchiveTranslator$dirty';
    }
    return '${workspace.displayName}$dirty';
  }

  void _syncControllerValues() {
    _syncTextController(_searchController, widget.controller.searchQuery);
    _syncTextController(_titleController, widget.controller.draftTitleCn);
    _syncTextController(_authorController, widget.controller.draftAuthorCn);
    _syncTextController(_contentController, widget.controller.draftContentCn);
  }

  void _syncTextController(TextEditingController controller, String value) {
    if (controller.text == value) {
      return;
    }
    controller.value = TextEditingValue(
      text: value,
      selection: TextSelection.collapsed(offset: value.length),
    );
  }

  Future<void> _pickWorkspace() async {
    if (!await _confirmDiscardChanges()) {
      return;
    }

    final success = await widget.controller.pickAndOpenWorkspace();
    if (!mounted || !success) {
      return;
    }
    setState(() {
      _mobilePaneIndex = 0;
    });
  }

  Future<void> _openRecentWorkspace(WorkspaceBookmark workspace) async {
    if (!await _confirmDiscardChanges()) {
      return;
    }

    final success = await widget.controller.openWorkspace(workspace);
    if (!mounted || !success) {
      return;
    }
    setState(() {
      _mobilePaneIndex = 0;
    });
  }

  Future<void> _reloadWorkspace() async {
    if (!await _confirmDiscardChanges()) {
      return;
    }
    await widget.controller.reloadWorkspace();
  }

  Future<void> _randomPick() async {
    if (!await _confirmDiscardChanges()) {
      return;
    }
    widget.controller.selectRandomEntry();
    if (!mounted) {
      return;
    }
    setState(() {
      _mobilePaneIndex = 1;
    });
  }

  Future<void> _saveCurrentEntry() async {
    await widget.controller.saveCurrentEntry();
  }

  Future<void> _copySourceCard(ArchiveEntry entry) async {
    await _copyCardText(
      text: buildSourceCardCopyText(entry),
      successMessage: '已複製原文',
    );
  }

  Future<void> _copyTranslationCard(ArchiveEntry entry) async {
    await _copyCardText(
      text: buildTranslationCardCopyText(entry),
      successMessage: '已複製譯文',
    );
  }

  Future<void> _copyCardText({
    required String? text,
    required String successMessage,
  }) async {
    if (!mounted) {
      return;
    }

    final messenger = ScaffoldMessenger.of(context);
    messenger.hideCurrentSnackBar();

    if (text == null || text.trim().isEmpty) {
      messenger.showSnackBar(
        const SnackBar(
          content: Text('沒有可複製的內容'),
          behavior: SnackBarBehavior.floating,
        ),
      );
      return;
    }

    await Clipboard.setData(ClipboardData(text: text));
    if (!mounted) {
      return;
    }

    messenger.showSnackBar(
      SnackBar(
        content: Text(successMessage),
        behavior: SnackBarBehavior.floating,
      ),
    );
  }

  Future<bool> _confirmDiscardChanges() async {
    if (!widget.controller.hasUnsavedChanges) {
      return true;
    }

    final result = await showDialog<bool>(
      context: context,
      builder: (context) {
        return AlertDialog(
          title: const Text('尚有未儲存修改'),
          content: const Text('你有尚未保存的變更。要先保存，還是放棄這些修改？'),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(context).pop(false),
              child: const Text('取消'),
            ),
            TextButton(
              onPressed: () => Navigator.of(context).pop(true),
              child: const Text('放棄修改'),
            ),
            FilledButton(
              onPressed: () async {
                final saved = await widget.controller.saveCurrentEntry();
                if (context.mounted) {
                  Navigator.of(context).pop(saved);
                }
              },
              child: const Text('先保存'),
            ),
          ],
        );
      },
    );

    return result ?? false;
  }

  Future<void> _showRecentWorkspacesSheet() async {
    final workspaces = widget.controller.settings.recentWorkspaces;
    if (workspaces.isEmpty) {
      return;
    }

    await showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      builder: (context) {
        return SafeArea(
          child: ListView.separated(
            shrinkWrap: true,
            padding: const EdgeInsets.fromLTRB(16, 0, 16, 24),
            itemCount: workspaces.length,
            separatorBuilder: (context, index) => const Divider(height: 1),
            itemBuilder: (context, index) {
              final workspace = workspaces[index];
              return ListTile(
                contentPadding: EdgeInsets.zero,
                title: Text(workspace.displayName),
                subtitle: Text(
                  workspace.archiveRelativePath.isEmpty
                      ? '.'
                      : workspace.archiveRelativePath,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
                trailing: const Icon(Icons.chevron_right),
                onTap: () async {
                  Navigator.of(context).pop();
                  await _openRecentWorkspace(workspace);
                },
              );
            },
          ),
        );
      },
    );
  }

  Future<void> _showWorkspaceInfoSheet() async {
    final workspace = widget.controller.currentWorkspace;
    final resolvedDirectory = widget.controller.resolvedDirectory;
    if (workspace == null) {
      return;
    }

    final stats = widget.controller.stats;
    await showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      isScrollControlled: true,
      builder: (context) {
        return SafeArea(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(16, 0, 16, 24),
            child: ListView(
              shrinkWrap: true,
              children: [
                Text(
                  workspace.displayName,
                  style: Theme.of(context).textTheme.titleLarge,
                ),
                const SizedBox(height: 16),
                _SheetInfoTile(
                  label: 'Archive root',
                  value: workspace.archiveRelativePath.isEmpty
                      ? '.'
                      : workspace.archiveRelativePath,
                ),
                _SheetInfoTile(
                  label: '解析方式',
                  value:
                      _resolutionSourceLabels[workspace.resolutionSource] ??
                      workspace.resolutionSource,
                ),
                _SheetInfoTile(label: 'Tree URI', value: workspace.treeUri),
                const SizedBox(height: 16),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: [
                    _SummaryChip(label: '全庫 ${stats.total}'),
                    _SummaryChip(label: '完成 ${stats.translated}'),
                    _SummaryChip(label: '部分 ${stats.partial}'),
                    _SummaryChip(label: '未翻譯 ${stats.untranslated}'),
                  ],
                ),
                if (resolvedDirectory != null &&
                    resolvedDirectory.notes.isNotEmpty) ...[
                  const SizedBox(height: 20),
                  Text('解析備註', style: Theme.of(context).textTheme.titleMedium),
                  const SizedBox(height: 8),
                  ...resolvedDirectory.notes.map(
                    (note) => Padding(
                      padding: const EdgeInsets.only(bottom: 8),
                      child: Text(note),
                    ),
                  ),
                ],
              ],
            ),
          ),
        );
      },
    );
  }

  Widget _buildMessages(BuildContext context) {
    final widgets = <Widget>[];

    if (widget.controller.errorMessage != null) {
      widgets.add(
        _MessageCard(
          color: Theme.of(context).colorScheme.errorContainer,
          icon: Icons.error_outline,
          message: widget.controller.errorMessage!,
          onDismiss: widget.controller.clearMessages,
        ),
      );
    }

    if (widget.controller.infoMessage != null) {
      widgets.add(
        _MessageCard(
          color: Theme.of(context).colorScheme.secondaryContainer,
          icon: Icons.info_outline,
          message: widget.controller.infoMessage!,
          onDismiss: widget.controller.clearMessages,
        ),
      );
    }

    if (widget.controller.warnings.isNotEmpty) {
      widgets.add(
        Card(
          color: Theme.of(
            context,
          ).colorScheme.tertiaryContainer.withValues(alpha: 0.55),
          child: Padding(
            padding: const EdgeInsets.all(12),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('載入警告', style: Theme.of(context).textTheme.titleSmall),
                const SizedBox(height: 8),
                ...widget.controller.warnings
                    .take(4)
                    .map(
                      (warning) => Padding(
                        padding: const EdgeInsets.only(bottom: 4),
                        child: Text('${warning.path}: ${warning.message}'),
                      ),
                    ),
                if (widget.controller.warnings.length > 4)
                  Text('另外還有 ${widget.controller.warnings.length - 4} 筆警告。'),
              ],
            ),
          ),
        ),
      );
    }

    return Column(
      children: widgets
          .map(
            (child) => Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: child,
            ),
          )
          .toList(growable: false),
    );
  }

  Widget _buildEmptyState(BuildContext context) {
    final recentWorkspaces = widget.controller.settings.recentWorkspaces;

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.translate, size: 48),
            const SizedBox(height: 16),
            Text(
              '選擇 Syncthing 已同步的工作目錄，開始在 Android 上進行 VerseArchiveTranslator 的人工翻譯與編修。',
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.bodyLarge,
            ),
            const SizedBox(height: 20),
            FilledButton.icon(
              onPressed: widget.controller.isBusy ? null : _pickWorkspace,
              icon: const Icon(Icons.folder_open),
              label: const Text('選擇資料夾'),
            ),
            if (recentWorkspaces.isNotEmpty) ...[
              const SizedBox(height: 24),
              Align(
                alignment: Alignment.centerLeft,
                child: Text(
                  '最近使用',
                  style: Theme.of(context).textTheme.titleSmall,
                ),
              ),
              const SizedBox(height: 8),
              ...recentWorkspaces
                  .take(5)
                  .map(
                    (workspace) => ListTile(
                      contentPadding: EdgeInsets.zero,
                      title: Text(workspace.displayName),
                      subtitle: Text(
                        workspace.archiveRelativePath.isEmpty
                            ? '.'
                            : workspace.archiveRelativePath,
                      ),
                      trailing: const Icon(Icons.chevron_right),
                      onTap: () => _openRecentWorkspace(workspace),
                    ),
                  ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildListPane(BuildContext context) {
    final entries = widget.controller.visibleEntries;
    final visibleStats = _buildStatsForEntries(entries);

    return Column(
      children: [
        _buildListControlsCard(
          context,
          entries: entries,
          visibleStats: visibleStats,
        ),
        const SizedBox(height: 12),
        Expanded(
          child: Card(
            clipBehavior: Clip.antiAlias,
            child: entries.isEmpty
                ? const Center(child: Text('目前沒有符合搜尋與篩選條件的內容。'))
                : ListView.separated(
                    padding: const EdgeInsets.all(12),
                    itemCount: entries.length,
                    separatorBuilder: (context, index) =>
                        const SizedBox(height: 8),
                    itemBuilder: (context, index) {
                      final entry = entries[index];
                      final selected =
                          widget.controller.selectedEntry != null &&
                          widget.controller.selectedEntry!.fileRelativePath ==
                              entry.fileRelativePath &&
                          widget.controller.selectedEntry!.index == entry.index;
                      return InkWell(
                        onTap: () => _handleEntryTap(entry),
                        borderRadius: BorderRadius.circular(14),
                        child: Ink(
                          decoration: BoxDecoration(
                            color: selected
                                ? Theme.of(context)
                                      .colorScheme
                                      .secondaryContainer
                                      .withValues(alpha: 0.72)
                                : Theme.of(context).colorScheme.surface,
                            borderRadius: BorderRadius.circular(14),
                            border: Border.all(
                              color: selected
                                  ? Theme.of(context).colorScheme.primary
                                  : Theme.of(
                                      context,
                                    ).colorScheme.outlineVariant,
                            ),
                          ),
                          child: Padding(
                            padding: const EdgeInsets.all(12),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Wrap(
                                  spacing: 8,
                                  runSpacing: 8,
                                  children: [
                                    _TinyBadge(
                                      label:
                                          _typeLabels[entry.typeLabel] ??
                                          entry.typeLabel,
                                    ),
                                    _TinyBadge(
                                      label:
                                          _translationLabels[translationState(
                                            entry.record,
                                          )] ??
                                          translationState(entry.record),
                                    ),
                                  ],
                                ),
                                const SizedBox(height: 8),
                                Text(
                                  entry.titleEn.isEmpty
                                      ? 'Untitled'
                                      : entry.titleEn,
                                  style: Theme.of(
                                    context,
                                  ).textTheme.titleMedium,
                                ),
                                const SizedBox(height: 4),
                                Text(
                                  entry.authorEn.isEmpty
                                      ? 'Unknown author'
                                      : entry.authorEn,
                                  style: Theme.of(context).textTheme.bodyMedium,
                                ),
                                const SizedBox(height: 8),
                                Text(
                                  entry.summary,
                                  maxLines: 3,
                                  overflow: TextOverflow.ellipsis,
                                ),
                                const SizedBox(height: 8),
                                Text(
                                  entry.fileName,
                                  style: Theme.of(context).textTheme.bodySmall,
                                ),
                              ],
                            ),
                          ),
                        ),
                      );
                    },
                  ),
          ),
        ),
      ],
    );
  }

  Widget _buildListControlsCard(
    BuildContext context, {
    required List<ArchiveEntry> entries,
    required ArchiveStats visibleStats,
  }) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          children: [
            TextField(
              controller: _searchController,
              onChanged: widget.controller.updateSearchQuery,
              decoration: const InputDecoration(
                labelText: '搜尋 author / title / content',
                prefixIcon: Icon(Icons.search),
              ),
            ),
            const SizedBox(height: 12),
            LayoutBuilder(
              builder: (context, constraints) {
                final compact = constraints.maxWidth < 560;
                if (compact) {
                  return Column(
                    children: [
                      _buildTypeFilterField(),
                      const SizedBox(height: 12),
                      _buildTranslationFilterField(),
                    ],
                  );
                }

                return Row(
                  children: [
                    Expanded(child: _buildTypeFilterField()),
                    const SizedBox(width: 12),
                    Expanded(child: _buildTranslationFilterField()),
                  ],
                );
              },
            ),
            const SizedBox(height: 12),
            Align(
              alignment: Alignment.centerLeft,
              child: Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  _SummaryChip(label: '結果 ${entries.length}'),
                  _SummaryChip(label: '完成 ${visibleStats.translated}'),
                  _SummaryChip(label: '部分 ${visibleStats.partial}'),
                  _SummaryChip(label: '未翻譯 ${visibleStats.untranslated}'),
                  ActionChip(
                    avatar: const Icon(Icons.casino_outlined, size: 18),
                    label: const Text('隨機'),
                    onPressed: widget.controller.hasWorkspace
                        ? _randomPick
                        : null,
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildTypeFilterField() {
    return DropdownButtonFormField<EntryTypeFilter>(
      initialValue: widget.controller.typeFilter,
      decoration: const InputDecoration(labelText: '類型'),
      items: const [
        DropdownMenuItem(value: EntryTypeFilter.all, child: Text('全部')),
        DropdownMenuItem(value: EntryTypeFilter.poems, child: Text('英文詩')),
        DropdownMenuItem(value: EntryTypeFilter.quotes, child: Text('哲學語錄')),
      ],
      onChanged: (value) {
        if (value != null) {
          widget.controller.updateTypeFilter(value);
        }
      },
    );
  }

  Widget _buildTranslationFilterField() {
    return DropdownButtonFormField<TranslationFilter>(
      initialValue: widget.controller.translationFilter,
      decoration: const InputDecoration(
        labelText: '隨機範圍',
        helperText: '只影響隨機挑選',
      ),
      items: const [
        DropdownMenuItem(value: TranslationFilter.all, child: Text('全部')),
        DropdownMenuItem(
          value: TranslationFilter.untranslated,
          child: Text('未翻譯'),
        ),
        DropdownMenuItem(value: TranslationFilter.partial, child: Text('部分翻譯')),
        DropdownMenuItem(
          value: TranslationFilter.translated,
          child: Text('已完成'),
        ),
      ],
      onChanged: (value) {
        if (value != null) {
          widget.controller.updateTranslationFilter(value);
        }
      },
    );
  }

  Future<void> _handleEntryTap(ArchiveEntry entry) async {
    if (!await _confirmDiscardChanges()) {
      return;
    }
    widget.controller.selectEntry(entry);
    if (!mounted) {
      return;
    }
    setState(() {
      _mobilePaneIndex = 1;
    });
  }

  Widget _buildEditorPane(
    BuildContext context, {
    required bool keyboardVisible,
  }) {
    final entry = widget.controller.selectedEntry;
    if (entry == null) {
      return Card(
        child: Center(
          child: Text(
            '從列表選擇一筆內容後，就能在這裡查看原文並編修譯文。',
            style: Theme.of(context).textTheme.bodyLarge,
            textAlign: TextAlign.center,
          ),
        ),
      );
    }

    final state = translationState(entry.record);
    final metadata = <_MetadataItem>[
      _MetadataItem(
        label: 'content.lines',
        value: '${recordLines(entry.record).length}',
      ),
      if (nestedString(entry.record, 'reason').isNotEmpty)
        _MetadataItem(
          label: 'reason',
          value: nestedString(entry.record, 'reason'),
        ),
      if (nestedString(entry.record, 'filter_detail').isNotEmpty)
        _MetadataItem(
          label: 'filter_detail',
          value: nestedString(entry.record, 'filter_detail'),
        ),
      if (nestedString(entry.record, 'source_tag').isNotEmpty)
        _MetadataItem(
          label: 'source_tag',
          value: nestedString(entry.record, 'source_tag'),
        ),
    ];

    return Column(
      children: [
        Card(
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  entry.fileName,
                  style: Theme.of(context).textTheme.titleMedium,
                ),
                const SizedBox(height: 6),
                Text(
                  '${_typeLabels[entry.typeLabel] ?? entry.typeLabel} · ${_translationLabels[state] ?? state} · index ${entry.index}',
                  style: Theme.of(context).textTheme.bodyMedium,
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 12),
        Expanded(
          child: Card(
            child: Column(
              children: [
                Expanded(
                  child: ListView(
                    controller: _editorScrollController,
                    padding: EdgeInsets.fromLTRB(
                      12,
                      12,
                      12,
                      keyboardVisible ? 24 : 12,
                    ),
                    children: [
                      _SectionCard(
                        title: '原文',
                        hintText: '長按複製',
                        onLongPress: () => _copySourceCard(entry),
                        child: Column(
                          children: [
                            _ReadonlyField(
                              label: 'title.en',
                              value: entry.titleEn,
                            ),
                            const SizedBox(height: 12),
                            _ReadonlyField(
                              label: 'author.en',
                              value: entry.authorEn,
                            ),
                            const SizedBox(height: 12),
                            _ReadonlyField(
                              label: 'content.en',
                              value: entry.contentEn,
                              maxLines: 14,
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(height: 12),
                      _SectionCard(
                        title: '譯文',
                        hintText: '長按複製',
                        onLongPress: () => _copyTranslationCard(entry),
                        child: Column(
                          children: [
                            _EditorField(
                              fieldKey: _titleFieldKey,
                              focusNode: _titleFocusNode,
                              controller: _titleController,
                              labelText: 'title.cn',
                              onChanged: widget.controller.updateDraftTitleCn,
                            ),
                            const SizedBox(height: 12),
                            _EditorField(
                              fieldKey: _authorFieldKey,
                              focusNode: _authorFocusNode,
                              controller: _authorController,
                              labelText: 'author.cn',
                              onChanged: widget.controller.updateDraftAuthorCn,
                            ),
                            const SizedBox(height: 12),
                            _EditorField(
                              fieldKey: _contentFieldKey,
                              focusNode: _contentFocusNode,
                              controller: _contentController,
                              labelText: 'content.cn',
                              minLines: 10,
                              maxLines: 18,
                              keyboardType: TextInputType.multiline,
                              onChanged: widget.controller.updateDraftContentCn,
                            ),
                          ],
                        ),
                      ),
                      if (metadata.isNotEmpty) ...[
                        const SizedBox(height: 12),
                        ExpansionTile(
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(16),
                            side: BorderSide(
                              color: Theme.of(
                                context,
                              ).colorScheme.outlineVariant,
                            ),
                          ),
                          collapsedShape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(16),
                            side: BorderSide(
                              color: Theme.of(
                                context,
                              ).colorScheme.outlineVariant,
                            ),
                          ),
                          tilePadding: const EdgeInsets.symmetric(
                            horizontal: 16,
                            vertical: 4,
                          ),
                          childrenPadding: const EdgeInsets.fromLTRB(
                            16,
                            0,
                            16,
                            16,
                          ),
                          title: const Text('更多資訊'),
                          children: metadata
                              .map(
                                (item) => _MetadataRow(
                                  label: item.label,
                                  value: item.value,
                                ),
                              )
                              .toList(growable: false),
                        ),
                      ],
                    ],
                  ),
                ),
                _buildEditorStatusBar(
                  context,
                  keyboardVisible: keyboardVisible,
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildEditorStatusBar(
    BuildContext context, {
    required bool keyboardVisible,
  }) {
    final dirty = widget.controller.hasUnsavedChanges;
    return SafeArea(
      top: false,
      child: Container(
        padding: const EdgeInsets.fromLTRB(12, 10, 12, 12),
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surfaceContainerLowest,
          border: Border(
            top: BorderSide(
              color: Theme.of(context).colorScheme.outlineVariant,
            ),
          ),
        ),
        child: Row(
          children: [
            Icon(
              dirty ? Icons.edit_outlined : Icons.check_circle_outline,
              size: 18,
            ),
            const SizedBox(width: 8),
            Expanded(
              child: Text(
                dirty ? '尚有未儲存修改' : '已與檔案同步',
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
            ),
            if (!keyboardVisible)
              FilledButton.icon(
                onPressed: widget.controller.canSave ? _saveCurrentEntry : null,
                icon: const Icon(Icons.save_outlined),
                label: const Text('保存'),
              ),
          ],
        ),
      ),
    );
  }
}

ArchiveStats _buildStatsForEntries(List<ArchiveEntry> entries) {
  var translated = 0;
  var partial = 0;
  var untranslated = 0;

  for (final entry in entries) {
    final state = translationState(entry.record);
    if (state == 'translated') {
      translated += 1;
    } else if (state == 'partial') {
      partial += 1;
    } else {
      untranslated += 1;
    }
  }

  return ArchiveStats(
    total: entries.length,
    translated: translated,
    partial: partial,
    untranslated: untranslated,
  );
}

class _MetadataItem {
  const _MetadataItem({required this.label, required this.value});

  final String label;
  final String value;
}

class _SummaryChip extends StatelessWidget {
  const _SummaryChip({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
      decoration: BoxDecoration(
        color: Theme.of(
          context,
        ).colorScheme.surfaceContainerHighest.withValues(alpha: 0.55),
        borderRadius: BorderRadius.circular(999),
      ),
      child: Text(label, style: Theme.of(context).textTheme.bodySmall),
    );
  }
}

class _TinyBadge extends StatelessWidget {
  const _TinyBadge({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surfaceContainerHighest,
        borderRadius: BorderRadius.circular(999),
      ),
      child: Text(label, style: Theme.of(context).textTheme.bodySmall),
    );
  }
}

class _SectionCard extends StatelessWidget {
  const _SectionCard({
    required this.title,
    required this.child,
    this.hintText,
    this.onLongPress,
  });

  final String title;
  final Widget child;
  final String? hintText;
  final VoidCallback? onLongPress;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.transparent,
      child: Ink(
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surfaceContainerLowest,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(
            color: Theme.of(context).colorScheme.outlineVariant,
          ),
        ),
        child: InkWell(
          borderRadius: BorderRadius.circular(16),
          onLongPress: onLongPress,
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Expanded(
                      child: Text(
                        title,
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                    ),
                    if (hintText != null)
                      Text(
                        hintText!,
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                  ],
                ),
                const SizedBox(height: 12),
                child,
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _ReadonlyField extends StatelessWidget {
  const _ReadonlyField({
    required this.label,
    required this.value,
    this.maxLines = 4,
  });

  final String label;
  final String value;
  final int maxLines;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: Theme.of(context).textTheme.labelLarge),
        const SizedBox(height: 6),
        Container(
          width: double.infinity,
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: Theme.of(
              context,
            ).colorScheme.surfaceContainerHighest.withValues(alpha: 0.35),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(
              color: Theme.of(context).colorScheme.outlineVariant,
            ),
          ),
          child: SelectableText(
            value.isEmpty ? ' ' : value,
            minLines: 1,
            maxLines: maxLines,
          ),
        ),
      ],
    );
  }
}

class _EditorField extends StatelessWidget {
  const _EditorField({
    required this.fieldKey,
    required this.focusNode,
    required this.controller,
    required this.labelText,
    required this.onChanged,
    this.minLines = 1,
    this.maxLines = 1,
    this.keyboardType,
  });

  final GlobalKey fieldKey;
  final FocusNode focusNode;
  final TextEditingController controller;
  final String labelText;
  final ValueChanged<String> onChanged;
  final int minLines;
  final int? maxLines;
  final TextInputType? keyboardType;

  @override
  Widget build(BuildContext context) {
    return KeyedSubtree(
      key: fieldKey,
      child: TextField(
        focusNode: focusNode,
        controller: controller,
        onChanged: onChanged,
        minLines: minLines,
        maxLines: maxLines,
        keyboardType: keyboardType,
        decoration: InputDecoration(
          labelText: labelText,
          alignLabelWithHint: maxLines == null || maxLines! > 1,
        ),
      ),
    );
  }
}

class _MetadataRow extends StatelessWidget {
  const _MetadataRow({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Text('$label: $value'),
    );
  }
}

class _SheetInfoTile extends StatelessWidget {
  const _SheetInfoTile({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label, style: Theme.of(context).textTheme.labelLarge),
          const SizedBox(height: 4),
          SelectableText(value),
        ],
      ),
    );
  }
}

class _MessageCard extends StatelessWidget {
  const _MessageCard({
    required this.color,
    required this.icon,
    required this.message,
    required this.onDismiss,
  });

  final Color color;
  final IconData icon;
  final String message;
  final VoidCallback onDismiss;

  @override
  Widget build(BuildContext context) {
    return Card(
      color: color,
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(icon),
            const SizedBox(width: 12),
            Expanded(child: Text(message)),
            IconButton(
              tooltip: '關閉',
              onPressed: onDismiss,
              icon: const Icon(Icons.close),
            ),
          ],
        ),
      ),
    );
  }
}
