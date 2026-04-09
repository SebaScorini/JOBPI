import { z } from 'zod';

export const MAX_PDF_SIZE_MB = 5;
export const MAX_PDF_SIZE_BYTES = MAX_PDF_SIZE_MB * 1024 * 1024;
export const MAX_CVS_PER_UPLOAD = 10;
export const MAX_JOB_DESCRIPTION_CHARS = 12000;

export const loginSchema = z.object({
  email: z.string().trim().min(1, 'Email is required.').email('Enter a valid email address.'),
  password: z.string().min(1, 'Password is required.'),
});

export const PASSWORD_MIN_LENGTH = 8;

export function getPasswordRequirementState(password: string) {
  return {
    minLength: password.length >= PASSWORD_MIN_LENGTH,
    uppercase: /[A-Z]/.test(password),
    lowercase: /[a-z]/.test(password),
    digit: /\d/.test(password),
  };
}

export const registerSchema = z.object({
  email: z.string().trim().min(1, 'Email is required.').email('Enter a valid email address.'),
  password: z
    .string()
    .min(PASSWORD_MIN_LENGTH, `Password must contain at least ${PASSWORD_MIN_LENGTH} characters.`)
    .refine((value) => /[A-Z]/.test(value), 'Password must contain at least one uppercase letter.')
    .refine((value) => /[a-z]/.test(value), 'Password must contain at least one lowercase letter.')
    .refine((value) => /\d/.test(value), 'Password must contain at least one number.'),
});

export const jobAnalysisSchema = z.object({
  title: z.string().trim().min(1, 'Job title is required.').max(200, 'Job title is too long.'),
  company: z.string().trim().min(1, 'Company is required.').max(200, 'Company is too long.'),
  description: z
    .string()
    .trim()
    .min(1, 'Job description is required.')
    .max(MAX_JOB_DESCRIPTION_CHARS, `Job description must be ${MAX_JOB_DESCRIPTION_CHARS} characters or fewer.`),
});

export function validateUploadFiles(files: File[]) {
  if (files.length === 0) {
    return 'Choose at least one PDF file.';
  }

  if (files.length > MAX_CVS_PER_UPLOAD) {
    return `You can upload up to ${MAX_CVS_PER_UPLOAD} CVs per request.`;
  }

  for (const file of files) {
    const fileName = file.name.toLowerCase();
    const isPdfMime = file.type === 'application/pdf' || file.type === 'application/octet-stream';
    if (!isPdfMime && !fileName.endsWith('.pdf')) {
      return `${file.name} must be a PDF file.`;
    }

    if (file.size > MAX_PDF_SIZE_BYTES) {
      return `${file.name} must be under ${MAX_PDF_SIZE_MB} MB.`;
    }
  }

  return null;
}
