# PR Review Command

Perform a comprehensive code review of pull request #$ARGUMENT. Analyze the changes with the same rigor as a senior engineer would apply during a thorough review process. You can use Github CLI (`gh`) to navigate Github related tasks.

## Review Scope

1. **Code Quality & Design**

   - Evaluate architectural decisions and design patterns
   - Assess code readability, maintainability, and adherence to SOLID principles
   - Check for code duplication and opportunities for refactoring
   - Review naming conventions for clarity and consistency

2. **Functionality & Logic**

   - Verify the implementation correctly addresses the stated requirements
   - Identify potential edge cases or error scenarios not handled
   - Check for off-by-one errors, null/undefined handling, and boundary conditions
   - Assess algorithm efficiency and potential performance bottlenecks

3. **Security Considerations**

   - Identify potential security vulnerabilities (injection, XSS, CSRF, etc.)
   - Review authentication/authorization logic if present
   - Check for exposed sensitive data or hardcoded credentials
   - Assess input validation and sanitization

4. **Testing**

   - Evaluate test coverage for new/modified code
   - Assess test quality and whether they effectively validate the changes
   - Identify missing test cases or scenarios
   - Check for proper mocking and test isolation

5. **Best Practices**

   - Verify adherence to project coding standards and style guides
   - Check for proper error handling and logging
   - Review dependency management and version compatibility
   - Assess documentation quality (comments, docstrings, README updates)

6. **Performance Impact**
   - Identify potential performance regressions
   - Review database queries for efficiency (N+1 problems, missing indexes)
   - Check for memory leaks or resource management issues
   - Assess impact on application startup time or critical paths

## Output Format

Provide your review in the following structure:

### Summary

Brief overview of the PR's purpose and your overall assessment.

### Critical Issues 🚨

Must-fix problems that block approval (security vulnerabilities, breaking changes, critical bugs).

### Major Concerns ⚠️

Significant issues that should be addressed (design flaws, missing tests, performance problems).

### Minor Suggestions 💡

Nice-to-have improvements (style issues, refactoring opportunities, documentation enhancements).

### Positive Feedback ✅

Highlight well-implemented aspects and good practices observed.

### Questions ❓

Clarifications needed about implementation choices or requirements.

## Review Guidelines

- Be constructive and specific in feedback
- Provide code examples for suggested improvements
- Reference line numbers when discussing specific code segments
- Consider the PR's context and stated objectives
- Balance thoroughness with pragmatism
- Suggest alternatives when criticizing an approach
