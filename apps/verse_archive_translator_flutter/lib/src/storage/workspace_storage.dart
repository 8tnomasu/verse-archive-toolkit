import 'dart:io';

import 'package:flutter/services.dart';

import '../models/archive_models.dart';

class PickedWorkspace {
  const PickedWorkspace({required this.treeUri, required this.displayName});

  factory PickedWorkspace.fromMap(Map<Object?, Object?> map) {
    return PickedWorkspace(
      treeUri: map.stringValue('treeUri'),
      displayName: map.stringValue('displayName'),
    );
  }

  final String treeUri;
  final String displayName;
}

class TextFileSnapshot {
  const TextFileSnapshot({
    required this.relativePath,
    required this.name,
    required this.content,
    required this.lastModified,
  });

  factory TextFileSnapshot.fromMap(Map<Object?, Object?> map) {
    return TextFileSnapshot(
      relativePath: map.stringValue('relativePath'),
      name: map.stringValue('name'),
      content: map.stringValue('content'),
      lastModified: map.intValue('lastModified'),
    );
  }

  final String relativePath;
  final String name;
  final String content;
  final int lastModified;
}

class WriteTextResult {
  const WriteTextResult({required this.lastModified});

  factory WriteTextResult.fromMap(Map<Object?, Object?> map) {
    return WriteTextResult(lastModified: map.intValue('lastModified'));
  }

  final int lastModified;
}

class StorageException implements Exception {
  const StorageException({
    required this.message,
    this.code = 'storage_error',
    this.details,
  });

  final String message;
  final String code;
  final Object? details;

  @override
  String toString() => message;
}

abstract class WorkspaceStorage {
  Future<PickedWorkspace?> pickWorkspace();

  Future<List<DirectoryItem>> listDirectory({
    required String treeUri,
    String relativePath = '',
  });

  Future<TextFileSnapshot> readTextFile({
    required String treeUri,
    required String relativePath,
  });

  Future<WriteTextResult> writeTextFileIfUnchanged({
    required String treeUri,
    required String relativePath,
    required int expectedLastModified,
    required String content,
  });
}

class MethodChannelWorkspaceStorage implements WorkspaceStorage {
  static const _channel = MethodChannel(
    'com.versearchive.verse_archive_translator_flutter/workspace',
  );

  @override
  Future<PickedWorkspace?> pickWorkspace() async {
    _ensureSupportedPlatform();
    final result = await _invokeMap('pickWorkspace');
    if (result == null) {
      return null;
    }
    return PickedWorkspace.fromMap(result);
  }

  @override
  Future<List<DirectoryItem>> listDirectory({
    required String treeUri,
    String relativePath = '',
  }) async {
    _ensureSupportedPlatform();
    final result = await _invokeList('listDirectory', <String, Object?>{
      'treeUri': treeUri,
      'relativePath': relativePath,
    });

    return result.map(DirectoryItem.fromMap).toList(growable: false);
  }

  @override
  Future<TextFileSnapshot> readTextFile({
    required String treeUri,
    required String relativePath,
  }) async {
    _ensureSupportedPlatform();
    final result = await _invokeMap('readTextFile', <String, Object?>{
      'treeUri': treeUri,
      'relativePath': relativePath,
    });
    if (result == null) {
      throw const StorageException(message: '找不到指定檔案。', code: 'not_found');
    }
    return TextFileSnapshot.fromMap(result);
  }

  @override
  Future<WriteTextResult> writeTextFileIfUnchanged({
    required String treeUri,
    required String relativePath,
    required int expectedLastModified,
    required String content,
  }) async {
    _ensureSupportedPlatform();
    final result =
        await _invokeMap('writeTextFileIfUnchanged', <String, Object?>{
          'treeUri': treeUri,
          'relativePath': relativePath,
          'expectedLastModified': expectedLastModified,
          'content': content,
        });
    if (result == null) {
      throw const StorageException(message: '檔案寫入失敗。');
    }
    return WriteTextResult.fromMap(result);
  }

  void _ensureSupportedPlatform() {
    if (!Platform.isAndroid) {
      throw const StorageException(
        message: '目前只有 Android 版實作了 Storage Access Framework 檔案存取。',
        code: 'unsupported_platform',
      );
    }
  }

  Future<Map<Object?, Object?>?> _invokeMap(
    String method, [
    Map<String, Object?>? arguments,
  ]) async {
    try {
      final result = await _channel.invokeMethod<Object?>(method, arguments);
      if (result == null) {
        return null;
      }
      if (result is! Map) {
        throw const StorageException(
          message: 'Android 端回傳了無法辨識的資料格式。',
          code: 'invalid_response',
        );
      }
      return result.map((key, value) => MapEntry(key, value));
    } on PlatformException catch (error) {
      throw StorageException(
        message: error.message ?? 'Android 檔案存取失敗。',
        code: error.code,
        details: error.details,
      );
    }
  }

  Future<List<Map<Object?, Object?>>> _invokeList(
    String method, [
    Map<String, Object?>? arguments,
  ]) async {
    try {
      final result = await _channel.invokeMethod<List<Object?>>(
        method,
        arguments,
      );
      if (result == null) {
        return const <Map<Object?, Object?>>[];
      }

      return result
          .whereType<Map>()
          .map((item) => item.map((key, value) => MapEntry(key, value)))
          .toList(growable: false);
    } on PlatformException catch (error) {
      throw StorageException(
        message: error.message ?? 'Android 檔案存取失敗。',
        code: error.code,
        details: error.details,
      );
    }
  }
}

extension on Map<Object?, Object?> {
  String stringValue(String key) {
    final value = this[key];
    return value is String ? value : '';
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
}
