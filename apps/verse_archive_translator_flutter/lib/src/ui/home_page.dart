import 'package:flutter/material.dart';

import '../controllers/translator_controller.dart';
import '../models/archive_models.dart';

const Map<String, String> _typeLabels = <String, String>{
  'english_poem': '英文詩',
  'philosophy': '哲思語錄',
};

const Map<String, String> _translationLabels = <String, String>{
  'translated': '已完成',
  'partial': '部分完成',
  'untranslated': '未翻譯',
};

const Map<String, String> _resolutionSourceLabels = <String, String>{
  'desktop_settings': '依桌面版 settings.json 解析',
  'selected_directory': '直接使用所選資料夾',
  'portable_output_child': '自動切到 portable output/ 子目錄',
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
  int _mobilePaneIndex = 0;

  @override
  void dispose() {
    _searchController.dispose();
    _titleController.dispose();
    _authorController.dispose();
    _contentController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: widget.controller,
      builder: (context, _) {
        _syncControllerValues();

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
            appBar: AppBar(
              title: Text(_buildAppBarTitle()),
              actions: [
                IconButton(
                  tooltip: '選擇資料夾',
                  onPressed: widget.controller.isBusy ? null : _pickWorkspace,
                  icon: const Icon(Icons.folder_open),
                ),
                PopupMenuButton<WorkspaceBookmark>(
                  tooltip: '最近使用',
                  enabled:
                      widget.controller.settings.recentWorkspaces.isNotEmpty,
                  onSelected: _openRecentWorkspace,
                  itemBuilder: (context) {
                    return widget.controller.settings.recentWorkspaces
                        .map(
                          (workspace) => PopupMenuItem<WorkspaceBookmark>(
                            value: workspace,
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                Text(workspace.displayName),
                                Text(
                                  workspace.archiveRelativePath.isEmpty
                                      ? '.'
                                      : workspace.archiveRelativePath,
                                  style: Theme.of(context).textTheme.bodySmall,
                                ),
                              ],
                            ),
                          ),
                        )
                        .toList(growable: false);
                  },
                  icon: const Icon(Icons.history),
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
                  tooltip: '隨機挑一筆',
                  onPressed:
                      widget.controller.hasWorkspace &&
                          !widget.controller.isBusy
                      ? _randomPick
                      : null,
                  icon: const Icon(Icons.casino_outlined),
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
            body: SafeArea(
              child: Column(
                children: [
                  if (widget.controller.isBusy || widget.controller.isSaving)
                    const LinearProgressIndicator(minHeight: 2),
                  Expanded(
                    child: Padding(
                      padding: const EdgeInsets.all(12),
                      child: Column(
                        children: [
                          _buildWorkspaceCard(context),
                          const SizedBox(height: 12),
                          _buildMessages(context),
                          if (!widget.controller.hasWorkspace)
                            Expanded(child: _buildEmptyState(context))
                          else
                            Expanded(
                              child: LayoutBuilder(
                                builder: (context, constraints) {
                                  final wideLayout =
                                      constraints.maxWidth >= 960;
                                  if (wideLayout) {
                                    return Row(
                                      crossAxisAlignment:
                                          CrossAxisAlignment.start,
                                      children: [
                                        SizedBox(
                                          width: 360,
                                          child: _buildListPane(context),
                                        ),
                                        const SizedBox(width: 12),
                                        Expanded(
                                          child: _buildEditorPane(context),
                                        ),
                                      ],
                                    );
                                  }

                                  return Column(
                                    children: [
                                      Expanded(
                                        child: IndexedStack(
                                          index: _mobilePaneIndex,
                                          children: [
                                            _buildListPane(context),
                                            _buildEditorPane(context),
                                          ],
                                        ),
                                      ),
                                      const SizedBox(height: 8),
                                      NavigationBar(
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
                                            icon: Icon(
                                              Icons.edit_note_outlined,
                                            ),
                                            selectedIcon: Icon(Icons.edit_note),
                                            label: '編修',
                                          ),
                                        ],
                                      ),
                                    ],
                                  );
                                },
                              ),
                            ),
                        ],
                      ),
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

  String _buildAppBarTitle() {
    final workspace = widget.controller.currentWorkspace;
    final dirty = widget.controller.hasUnsavedChanges ? ' • 未儲存' : '';
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

  Future<bool> _confirmDiscardChanges() async {
    if (!widget.controller.hasUnsavedChanges) {
      return true;
    }

    final result = await showDialog<bool>(
      context: context,
      builder: (context) {
        return AlertDialog(
          title: const Text('尚有未儲存修改'),
          content: const Text('你目前的譯文尚未保存。要先保存，還是放棄這些變更？'),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(context).pop(false),
              child: const Text('取消'),
            ),
            TextButton(
              onPressed: () => Navigator.of(context).pop(true),
              child: const Text('放棄變更'),
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

  Widget _buildWorkspaceCard(BuildContext context) {
    final workspace = widget.controller.currentWorkspace;
    final resolvedDirectory = widget.controller.resolvedDirectory;
    final stats = widget.controller.stats;

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.folder_copy_outlined),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    workspace?.displayName ?? '尚未選擇工作資料夾',
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                ),
                FilledButton.tonalIcon(
                  onPressed: widget.controller.isBusy ? null : _pickWorkspace,
                  icon: const Icon(Icons.folder_open),
                  label: Text(workspace == null ? '選擇資料夾' : '更換資料夾'),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                _InfoChip(
                  label: '資料根目錄',
                  value:
                      workspace == null || workspace.archiveRelativePath.isEmpty
                      ? '.'
                      : workspace.archiveRelativePath,
                ),
                if (resolvedDirectory != null)
                  _InfoChip(
                    label: '解析方式',
                    value:
                        _resolutionSourceLabels[resolvedDirectory.source] ??
                        resolvedDirectory.source,
                  ),
                _InfoChip(label: '總筆數', value: '${stats.total}'),
                _InfoChip(label: '已完成', value: '${stats.translated}'),
                _InfoChip(label: '部分完成', value: '${stats.partial}'),
                _InfoChip(label: '未翻譯', value: '${stats.untranslated}'),
              ],
            ),
            if (resolvedDirectory != null &&
                resolvedDirectory.notes.isNotEmpty) ...[
              const SizedBox(height: 12),
              ...resolvedDirectory.notes.map(
                (note) => Padding(
                  padding: const EdgeInsets.only(bottom: 4),
                  child: Text('• $note'),
                ),
              ),
            ],
          ],
        ),
      ),
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
          ).colorScheme.tertiaryContainer.withValues(alpha: 0.5),
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
                        child: Text('• ${warning.path}: ${warning.message}'),
                      ),
                    ),
                if (widget.controller.warnings.length > 4)
                  Text('另有 ${widget.controller.warnings.length - 4} 筆警告未展開顯示。'),
              ],
            ),
          ),
        ),
      );
    }

    if (widgets.isEmpty) {
      return const SizedBox.shrink();
    }

    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Column(
        children: widgets
            .map(
              (child) => Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: child,
              ),
            )
            .toList(growable: false),
      ),
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
              '用 Android 直接打開 Syncthing 同步下來的資料夾，讀取與桌面版 VerseArchiveTranslator 相容的 JSON。',
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.bodyLarge,
            ),
            const SizedBox(height: 20),
            FilledButton.icon(
              onPressed: widget.controller.isBusy ? null : _pickWorkspace,
              icon: const Icon(Icons.folder_open),
              label: const Text('選擇工作資料夾'),
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

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          children: [
            TextField(
              controller: _searchController,
              onChanged: widget.controller.updateSearchQuery,
              decoration: const InputDecoration(
                labelText: '搜尋 author/title/content',
                prefixIcon: Icon(Icons.search),
              ),
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: DropdownButtonFormField<EntryTypeFilter>(
                    initialValue: widget.controller.typeFilter,
                    decoration: const InputDecoration(labelText: '類型'),
                    items: const [
                      DropdownMenuItem(
                        value: EntryTypeFilter.all,
                        child: Text('全部'),
                      ),
                      DropdownMenuItem(
                        value: EntryTypeFilter.poems,
                        child: Text('英文詩'),
                      ),
                      DropdownMenuItem(
                        value: EntryTypeFilter.quotes,
                        child: Text('哲思語錄'),
                      ),
                    ],
                    onChanged: (value) {
                      if (value != null) {
                        widget.controller.updateTypeFilter(value);
                      }
                    },
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: DropdownButtonFormField<TranslationFilter>(
                    initialValue: widget.controller.translationFilter,
                    decoration: const InputDecoration(labelText: '翻譯狀態'),
                    items: const [
                      DropdownMenuItem(
                        value: TranslationFilter.all,
                        child: Text('全部'),
                      ),
                      DropdownMenuItem(
                        value: TranslationFilter.untranslated,
                        child: Text('未翻譯'),
                      ),
                      DropdownMenuItem(
                        value: TranslationFilter.partial,
                        child: Text('部分完成'),
                      ),
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
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                Text(
                  '結果 ${entries.length}',
                  style: Theme.of(context).textTheme.titleSmall,
                ),
                const Spacer(),
                TextButton.icon(
                  onPressed: widget.controller.hasWorkspace
                      ? _randomPick
                      : null,
                  icon: const Icon(Icons.casino_outlined),
                  label: const Text('隨機'),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Expanded(
              child: entries.isEmpty
                  ? const Center(child: Text('目前沒有符合條件的資料。'))
                  : ListView.separated(
                      itemCount: entries.length,
                      separatorBuilder: (context, index) =>
                          const SizedBox(height: 8),
                      itemBuilder: (context, index) {
                        final entry = entries[index];
                        final selected =
                            widget.controller.selectedEntry != null &&
                            widget.controller.selectedEntry!.fileRelativePath ==
                                entry.fileRelativePath &&
                            widget.controller.selectedEntry!.index ==
                                entry.index;
                        return InkWell(
                          onTap: () => _handleEntryTap(entry),
                          borderRadius: BorderRadius.circular(12),
                          child: Ink(
                            decoration: BoxDecoration(
                              color: selected
                                  ? Theme.of(context)
                                        .colorScheme
                                        .secondaryContainer
                                        .withValues(alpha: 0.75)
                                  : Colors.white,
                              borderRadius: BorderRadius.circular(12),
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
                                      Text(
                                        entry.fileName,
                                        style: Theme.of(
                                          context,
                                        ).textTheme.bodySmall,
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
                                  ),
                                  const SizedBox(height: 8),
                                  Text(
                                    entry.summary,
                                    maxLines: 3,
                                    overflow: TextOverflow.ellipsis,
                                  ),
                                ],
                              ),
                            ),
                          ),
                        );
                      },
                    ),
            ),
          ],
        ),
      ),
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

  Widget _buildEditorPane(BuildContext context) {
    final entry = widget.controller.selectedEntry;
    if (entry == null) {
      return Card(
        child: Center(
          child: Text(
            '請先從列表選擇一筆資料。',
            style: Theme.of(context).textTheme.bodyLarge,
          ),
        ),
      );
    }

    final state = translationState(entry.record);

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                _InfoChip(label: '檔案', value: entry.fileName),
                _InfoChip(
                  label: '類型',
                  value: _typeLabels[entry.typeLabel] ?? entry.typeLabel,
                ),
                _InfoChip(
                  label: '狀態',
                  value: _translationLabels[state] ?? state,
                ),
                _InfoChip(label: '索引', value: '${entry.index}'),
              ],
            ),
            const SizedBox(height: 16),
            Expanded(
              child: ListView(
                children: [
                  _SectionCard(
                    title: '原文',
                    child: Column(
                      children: [
                        _ReadonlyField(label: 'title.en', value: entry.titleEn),
                        const SizedBox(height: 12),
                        _ReadonlyField(
                          label: 'author.en',
                          value: entry.authorEn,
                        ),
                        const SizedBox(height: 12),
                        _ReadonlyField(
                          label: 'content.en',
                          value: entry.contentEn,
                          maxLines: 12,
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 12),
                  _SectionCard(
                    title: '譯文編修',
                    child: Column(
                      children: [
                        TextField(
                          controller: _titleController,
                          onChanged: widget.controller.updateDraftTitleCn,
                          decoration: const InputDecoration(
                            labelText: 'title.cn',
                          ),
                        ),
                        const SizedBox(height: 12),
                        TextField(
                          controller: _authorController,
                          onChanged: widget.controller.updateDraftAuthorCn,
                          decoration: const InputDecoration(
                            labelText: 'author.cn',
                          ),
                        ),
                        const SizedBox(height: 12),
                        TextField(
                          controller: _contentController,
                          onChanged: widget.controller.updateDraftContentCn,
                          minLines: 8,
                          maxLines: 16,
                          decoration: const InputDecoration(
                            labelText: 'content.cn',
                            alignLabelWithHint: true,
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 12),
                  _SectionCard(
                    title: 'Metadata',
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        _MetadataRow(
                          label: 'content.lines',
                          value: '${recordLines(entry.record).length} 行',
                        ),
                        if (nestedString(entry.record, 'reason').isNotEmpty)
                          _MetadataRow(
                            label: 'reason',
                            value: nestedString(entry.record, 'reason'),
                          ),
                        if (nestedString(
                          entry.record,
                          'filter_detail',
                        ).isNotEmpty)
                          _MetadataRow(
                            label: 'filter_detail',
                            value: nestedString(entry.record, 'filter_detail'),
                          ),
                        if (nestedString(entry.record, 'source_tag').isNotEmpty)
                          _MetadataRow(
                            label: 'source_tag',
                            value: nestedString(entry.record, 'source_tag'),
                          ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: Text(
                    widget.controller.hasUnsavedChanges ? '有未儲存修改' : '已與檔案同步',
                  ),
                ),
                const SizedBox(width: 12),
                FilledButton.icon(
                  onPressed: widget.controller.canSave
                      ? _saveCurrentEntry
                      : null,
                  icon: const Icon(Icons.save_outlined),
                  label: const Text('保存'),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _InfoChip extends StatelessWidget {
  const _InfoChip({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
      decoration: BoxDecoration(
        color: Theme.of(
          context,
        ).colorScheme.surfaceContainerHighest.withValues(alpha: 0.55),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Text('$label: $value'),
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
  const _SectionCard({required this.title, required this.child});

  final String title;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surfaceContainerLowest,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Theme.of(context).colorScheme.outlineVariant),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title, style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 12),
          child,
        ],
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
