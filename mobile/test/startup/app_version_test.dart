import 'package:chosung/startup/app_version.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('isUpdateRequired', () {
    test('같은 버전이면 업데이트가 필요하지 않다', () {
      expect(isUpdateRequired(current: '1.0.0', minimum: '1.0.0'), isFalse);
    });

    test('현재 버전이 더 높으면 필요하지 않다', () {
      expect(isUpdateRequired(current: '1.2.0', minimum: '1.1.9'), isFalse);
      expect(isUpdateRequired(current: '2.0.0', minimum: '1.9.9'), isFalse);
    });

    test('현재 버전이 더 낮으면 필요하다', () {
      expect(isUpdateRequired(current: '1.0.0', minimum: '1.0.1'), isTrue);
      expect(isUpdateRequired(current: '1.9.9', minimum: '2.0.0'), isTrue);
    });

    test('자릿수를 문자열이 아니라 숫자로 비교한다', () {
      expect(isUpdateRequired(current: '1.10.0', minimum: '1.9.0'), isFalse);
      expect(isUpdateRequired(current: '1.9.0', minimum: '1.10.0'), isTrue);
    });

    test('마디 개수가 달라도 빠진 자리를 0 으로 본다', () {
      expect(isUpdateRequired(current: '1.0', minimum: '1.0.0'), isFalse);
      expect(isUpdateRequired(current: '1.0', minimum: '1.0.1'), isTrue);
      expect(isUpdateRequired(current: '1.0.0.1', minimum: '1.0.0'), isFalse);
    });

    test('빌드 번호(+N)는 비교에서 무시한다', () {
      expect(isUpdateRequired(current: '1.0.0+7', minimum: '1.0.0'), isFalse);
      expect(isUpdateRequired(current: '1.0.0', minimum: '1.0.1+2'), isTrue);
    });

    // 파싱 실패로 사용자를 앱 밖에 세워두는 쪽이 더 큰 사고다 — 열어주는 쪽으로 기운다.
    test('읽을 수 없는 버전 문자열이면 막지 않는다', () {
      expect(isUpdateRequired(current: '', minimum: '1.0.0'), isFalse);
      expect(isUpdateRequired(current: '1.0.0', minimum: 'latest'), isFalse);
      expect(isUpdateRequired(current: 'dev', minimum: '1.0.0'), isFalse);
    });
  });
}
