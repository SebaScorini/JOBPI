const NOISE_PATTERNS = [
  /\bequal opportunity\b/i,
  /\beeo\b/i,
  /\ball qualified applicants\b/i,
  /\bdiversity\b/i,
  /\binclusion\b/i,
  /\baccommodation(s)?\b/i,
  /\bprivacy policy\b/i,
  /\bterms of use\b/i,
  /\bcompany culture\b/i,
  /\bour values\b/i,
  /\bbenefits\b/i,
  /\bperks\b/i,
  /\bcompensation\b/i,
  /\bsalary\b/i,
  /\babout (the )?company\b/i,
  /\bwhy join us\b/i,
  /\bmission\b/i,
  /\bculture\b/i,
  /\bwork environment\b/i,
  /\bmedical\b/i,
  /\b401\(k\)\b/i,
  /\bparental leave\b/i,
  /\bvisa sponsorship\b/i,
];

const JOB_SECTION_PATTERNS: Record<string, RegExp> = {
  requirements: /(requirement|qualification|must have|what you bring|what we're looking for|ideal candidate)/i,
  preferred: /(preferred|nice to have|bonus|plus)/i,
  responsibilities: /(responsibilit|what you('| wi)ll do|what you'll work on|day to day|key duties)/i,
  role: /(about the role|role overview|position overview|summary)/i,
  skills: /(skills?|tech stack|technology|tools?|stack)/i,
  experience: /(experience|background)/i,
};

const JOB_SECTION_PRIORITY: Record<string, number> = {
  requirements: 10,
  responsibilities: 9,
  skills: 8,
  experience: 7,
  preferred: 6,
  role: 5,
};

const HIGH_SIGNAL_KEYWORDS = [
  'swift',
  'vapor',
  'react',
  'sql',
  'postgres',
  'psql',
  'aws',
  'api',
  'backend',
  'frontend',
  'mobile',
  'server-side',
  'design',
  'build',
  'develop',
  'scale',
  'optimize',
  'required',
  'preferred',
  'experience',
  'qualifications',
];

export interface JobDescriptionPreview {
  compactedText: string;
  originalChars: number;
  compactedChars: number;
  savedChars: number;
  changed: boolean;
}

function normalizeLine(value: string): string {
  return value.replace(/\r/g, ' ').replace(/\t/g, ' ').replace(/\s+/g, ' ').trim().replace(/^[\-\*\u2022]\s*/, '');
}

function looksLikeHeading(line: string): boolean {
  return line.length <= 80 && (line.endsWith(':') || line === line.toUpperCase());
}

function matchSection(line: string): string | null {
  if (!looksLikeHeading(line)) {
    return null;
  }

  for (const [section, pattern] of Object.entries(JOB_SECTION_PATTERNS)) {
    if (pattern.test(line)) {
      return section;
    }
  }

  return null;
}

function isNoise(line: string): boolean {
  if (line.length < 4) {
    return true;
  }
  return NOISE_PATTERNS.some((pattern) => pattern.test(line));
}

function scoreLine(line: string, section: string | null): number {
  const lowered = line.toLowerCase();
  let score = JOB_SECTION_PRIORITY[section ?? ''] ?? 0;

  if (Object.values(JOB_SECTION_PATTERNS).some((pattern) => pattern.test(line))) {
    score += 4;
  }
  if (HIGH_SIGNAL_KEYWORDS.some((keyword) => lowered.includes(keyword))) {
    score += 4;
  }
  if (/\b(must|required|responsible|experience with|proficiency|knowledge)\b/i.test(line)) {
    score += 3;
  }
  if (line.length <= 160) {
    score += 1;
  }

  return score;
}

function dedupeLines(lines: string[]): string[] {
  const seen = new Set<string>();
  const unique: string[] = [];

  for (const line of lines) {
    const key = line.toLowerCase();
    if (!line || seen.has(key)) {
      continue;
    }
    seen.add(key);
    unique.push(line);
  }

  return unique;
}

function joinWithinLimit(lines: string[], maxChars: number): string {
  const selected: string[] = [];
  let total = 0;

  for (const line of lines) {
    const addition = line.length + (selected.length > 0 ? 1 : 0);
    if (total + addition > maxChars) {
      continue;
    }
    selected.push(line);
    total += addition;
  }

  return selected.join('\n').trim();
}

export function buildImportantJobDetailsPreview(text: string, maxChars: number): JobDescriptionPreview {
  const original = text.trim();
  if (!original) {
    return {
      compactedText: '',
      originalChars: 0,
      compactedChars: 0,
      savedChars: 0,
      changed: false,
    };
  }

  const normalizedLines = dedupeLines(
    original
      .replace(/\r\n?/g, '\n')
      .split('\n')
      .map((line) => normalizeLine(line))
      .filter((line) => line && !isNoise(line)),
  );

  let currentSection: string | null = null;
  const candidates: Array<{ score: number; index: number; line: string }> = [];

  normalizedLines.forEach((line, index) => {
    const matchedSection = matchSection(line);
    if (matchedSection) {
      currentSection = matchedSection;
      candidates.push({
        score: (JOB_SECTION_PRIORITY[matchedSection] ?? 0) + 2,
        index,
        line: line.replace(/:$/, ''),
      });
      return;
    }

    const score = scoreLine(line, currentSection);
    if (score <= 0) {
      return;
    }

    candidates.push({ score, index, line });
  });

  const ordered = dedupeLines(
    candidates
      .sort((a, b) => b.score - a.score || a.index - b.index)
      .map((item) => item.line),
  );

  const compactedText = joinWithinLimit(ordered, maxChars);
  const compactedChars = compactedText.length;

  return {
    compactedText,
    originalChars: original.length,
    compactedChars,
    savedChars: Math.max(0, original.length - compactedChars),
    changed: compactedText.length > 0 && compactedText !== original,
  };
}
