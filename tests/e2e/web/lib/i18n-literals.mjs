/** 번역문 자체를 검증해야 하는 자리. 서버 사전에서 뽑아오면 사전이 틀려도
 *  통과하므로, 테스트가 기대값을 직접 적는다(브리프 시나리오 3·6).
 *
 *  고치는 조건: 제품이 이 표기를 **의도적으로** 바꿀 때만. 테스트가 깨졌다고
 *  여기 값을 서버 사전에 맞추면 검증이 사라진다.
 */
export const LITERALS = {
  ko: {
    guestPrefix: "게스트 #",
    attemptsOne: "1회",
    attemptsThree: "3회",
    appTitle: "오늘의 초성",
    navLeaderboard: "순위",
    navRecords: "내 기록",
    navToday: "오늘",
    puzzleLanguageChipKo: "한국어",
    puzzleLanguageChipEn: "English",
  },
  en: {
    guestPrefix: "Guest #",
    attemptsOne: "1 try",
    attemptsThree: "3 tries",
    appTitle: "Hidden Vowels",
    navLeaderboard: "Leaderboard",
    navRecords: "My record",
    navToday: "Today",
    puzzleLanguageChipKo: "Korean",
    puzzleLanguageChipEn: "English",
  },
};
