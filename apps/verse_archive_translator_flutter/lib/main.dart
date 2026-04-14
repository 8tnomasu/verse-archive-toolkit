import 'package:flutter/material.dart';

import 'src/app.dart';
import 'src/controllers/translator_controller.dart';
import 'src/services/archive_repository.dart';
import 'src/services/preferences_store.dart';
import 'src/storage/workspace_storage.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  final controller = TranslatorController(
    repository: ArchiveRepository(MethodChannelWorkspaceStorage()),
    preferencesStore: PreferencesStore(),
  );

  runApp(VerseArchiveTranslatorApp(controller: controller));
}
