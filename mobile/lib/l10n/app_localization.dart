import 'package:flutter/material.dart';

/// UI 문구 언어. 퍼즐 언어(`puzzle_language`)와 별개다 — UI 는 기기 설정을
/// 따르고(수동 토글 없음), 퍼즐 언어는 서버에 저장되는 사용자 선호다.
abstract final class AppLocalization {
  static const ko = Locale('ko');
  static const en = Locale('en');

  static const List<Locale> supportedLocales = [ko, en];
  static const Locale fallbackLocale = ko;
  static const path = 'assets/translations';
}
