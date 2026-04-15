# Changelog

All notable changes to JOBPI will be documented in this file.

## [2026-04-15] - Sprint 8 Polish & Supabase Migration

### Added
- **Supabase Authentication**: Integrated full auth flow (Login, Register, Forgot/Reset Password) using Supabase Auth.
- **CV Storage Service**: CV files are now stored in Supabase Storage buckets instead of local disks.
- **Audit Fields**: Added `updated_at` and `deleted_at` fields to core entities (Jobs, CVs) for better tracking.
- **Soft-Delete**: Implemented logic to preserve data while hiding it from the UI.
- **Framer Motion Integration**: Added fluid entrance animations and micro-interactions across the dashboard.
- **Job Analysis Loading Experience**: New visual feedback during heavy AI processing.
- **Frontend Localization**: Expanded English and Spanish translation coverage.

### Changed
- **Database Schema**: Significant updates to support Supabase user IDs and storage paths.
- **CRUD Layer**: Refactored to handle soft-deletion and resource filtering by user ID.
- **API Security**: Standardized on Supabase-compatible dependency injection for protected routes.
- **UI Design**: Upgraded dashboard panels with modern typography and vibrant color palettes.

### Fixed
- **Auth Flow**: Resolved issues with token validation and session persistence.
- **Test Suites**: Updated global integration tests to reflect new AI workflows and auth requirements.
