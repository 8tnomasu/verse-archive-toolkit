import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:verse_archive_translator_flutter/src/models/archive_models.dart';
import 'package:verse_archive_translator_flutter/src/services/preferences_store.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test(
    'PreferencesStore persists recent workspace treeUri and bookmark fields',
    () async {
      SharedPreferences.setMockInitialValues(<String, Object>{});

      final store = PreferencesStore();
      final settings = TranslatorAppSettings(
        recentWorkspaces: <WorkspaceBookmark>[
          WorkspaceBookmark(
            treeUri: 'content://workspace/root',
            displayName: 'Syncthing',
            archiveRelativePath: 'output',
            resolutionSource: 'desktop_settings',
            lastOpenedAt: DateTime.parse('2026-04-15T12:34:56Z'),
          ),
        ],
      );

      await store.save(settings);
      final loaded = await store.load();
      final bookmark = loaded.lastWorkspace;

      expect(bookmark, isNotNull);
      expect(bookmark!.treeUri, 'content://workspace/root');
      expect(bookmark.displayName, 'Syncthing');
      expect(bookmark.archiveRelativePath, 'output');
      expect(bookmark.resolutionSource, 'desktop_settings');
      expect(bookmark.lastOpenedAt, DateTime.parse('2026-04-15T12:34:56.000Z'));
    },
  );
}
