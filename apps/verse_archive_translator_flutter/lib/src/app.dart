import 'package:flutter/material.dart';

import 'controllers/translator_controller.dart';
import 'ui/home_page.dart';

class VerseArchiveTranslatorApp extends StatefulWidget {
  const VerseArchiveTranslatorApp({required this.controller, super.key});

  final TranslatorController controller;

  @override
  State<VerseArchiveTranslatorApp> createState() =>
      _VerseArchiveTranslatorAppState();
}

class _VerseArchiveTranslatorAppState extends State<VerseArchiveTranslatorApp> {
  late final Future<void> _initialization = widget.controller.initialize();

  @override
  void dispose() {
    widget.controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final colorScheme = ColorScheme.fromSeed(
      seedColor: const Color(0xFF55684C),
      brightness: Brightness.light,
    );

    return MaterialApp(
      title: 'VerseArchiveTranslator',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        useMaterial3: true,
        colorScheme: colorScheme,
        scaffoldBackgroundColor: const Color(0xFFF3F0E7),
        cardTheme: const CardThemeData(
          margin: EdgeInsets.zero,
          elevation: 0,
          color: Colors.white,
        ),
        inputDecorationTheme: const InputDecorationTheme(
          border: OutlineInputBorder(),
          filled: true,
          fillColor: Colors.white,
          isDense: true,
        ),
      ),
      home: FutureBuilder<void>(
        future: _initialization,
        builder: (context, snapshot) {
          if (snapshot.connectionState != ConnectionState.done) {
            return const Scaffold(
              body: Center(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    CircularProgressIndicator(),
                    SizedBox(height: 16),
                    Text('Loading VerseArchiveTranslator...'),
                  ],
                ),
              ),
            );
          }

          return TranslatorHomePage(controller: widget.controller);
        },
      ),
    );
  }
}
