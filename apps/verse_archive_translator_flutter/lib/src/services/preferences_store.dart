import 'dart:convert';

import 'package:shared_preferences/shared_preferences.dart';

import '../models/archive_models.dart';

class PreferencesStore {
  static const _settingsKey = 'translator_settings_v1';

  Future<TranslatorAppSettings> load() async {
    final preferences = await SharedPreferences.getInstance();
    final raw = preferences.getString(_settingsKey);
    if (raw == null || raw.trim().isEmpty) {
      return TranslatorAppSettings.empty();
    }

    try {
      final decoded = jsonDecode(raw);
      if (decoded is! Map) {
        return TranslatorAppSettings.empty();
      }
      return TranslatorAppSettings.fromJson(
        decoded.map((key, value) => MapEntry(key.toString(), value)),
      );
    } catch (_) {
      return TranslatorAppSettings.empty();
    }
  }

  Future<void> save(TranslatorAppSettings settings) async {
    final preferences = await SharedPreferences.getInstance();
    await preferences.setString(_settingsKey, jsonEncode(settings.toJson()));
  }
}
