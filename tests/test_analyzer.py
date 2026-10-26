import unittest
from analyzer import analyze_notice

class AnalyzeNoticeTests(unittest.TestCase):
    def test_extracts_common_notice_sections(self):
        text = """Deadline: 27 Oct 2026 @ 8:30am GMT+5:30. Submit before the deadline.
        Eligibility: Students only. You may participate individually or in a team of up to four people.
        What to submit: a public source-code repository, a 1–3 minute demo video, and at least one screenshot.
        AI tools may be used. Explain how you used them and credit AI assistance.
        Do not include passwords, API keys, or private information.
        Projects will be judged on creativity, impact, technical execution, and user experience."""
        result = analyze_notice(text)
        categories = {item['category'] for item in result['findings']}
        self.assertIn('Deadline', categories)
        self.assertIn('Eligibility', categories)
        self.assertIn('What to submit', categories)
        self.assertIn('Restrictions & risks', categories)
        self.assertIn('Judging criteria', categories)
        self.assertTrue(result['dates'])
        self.assertTrue(result['dates'][0]['raw'].startswith('27 Oct 2026 @ 8:30am GMT+5:30'))
        self.assertNotIn('Submit before the deadline', result['dates'][0]['raw'])
        self.assertTrue(any('public source-code repository' in f['evidence'] for f in result['findings']))

    def test_short_input_raises_helpful_error(self):
        with self.assertRaises(ValueError):
            analyze_notice('too short')

    def test_review_prompts_are_review_hints_not_assertions(self):
        result = analyze_notice('The notice says students should apply before the closing date and prepare a small demo project.')
        self.assertIsInstance(result['review_prompts'], list)
        self.assertIn('method', result)

if __name__ == '__main__':
    unittest.main()
