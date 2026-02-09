# 🔧 Avatar Adam - Frontend Fixes Guide

**Date:** February 7, 2026  
**Status:** 5 Errors, 9 Warnings Found  
**Estimated Fix Time:** 1-2 hours

---

## 🚀 Quick Start

### Option 1: Auto-Fix (Recommended First Step)
```bash
cd frontend
npm run lint -- --fix
```

This will automatically fix:
- Unused variables (prefixed with underscore)
- Some formatting issues

### Option 2: Manual Fixes (Required for Some Issues)
Follow the detailed fixes below for issues that can't be auto-fixed.

---

## 🔴 Critical Errors (Must Fix)

### Error 1: Case Block Declaration (useVoiceChat.ts:286)

**File:** `src/hooks/useVoiceChat.ts`  
**Line:** 286  
**Issue:** Variable declared in case block without block scope

**Current Code:**
```typescript
case 'STOP':
  const audioData = ...
  // more code
  break;
```

**Fixed Code:**
```typescript
case 'STOP': {
  const audioData = ...
  // more code
  break;
}
```

**Why:** JavaScript requires block scope for variable declarations in case statements.

---

### Error 2: Case Block Declaration (VoiceChat.tsx:339)

**File:** `src/pages/VoiceChat.tsx`  
**Line:** 339  
**Issue:** Variable declared in case block without block scope

**Current Code:**
```typescript
case 'STOP':
  const audioData = ...
  // more code
  break;
```

**Fixed Code:**
```typescript
case 'STOP': {
  const audioData = ...
  // more code
  break;
}
```

**Why:** Same as Error 1 - JavaScript requires block scope.

---

### Error 3: Unused Variable (VoiceCall.tsx:95)

**File:** `src/pages/VoiceCall.tsx`  
**Line:** 95  
**Issue:** Variable assigned but never used

**Current Code:**
```typescript
const _avatarTranscript = response.data.transcript;
```

**Option A: Remove if not needed**
```typescript
// Remove the line entirely if not needed
```

**Option B: Use the variable**
```typescript
const avatarTranscript = response.data.transcript;
// Then use it somewhere in the code
setAvatarTranscript(avatarTranscript);
```

**Why:** Unused variables indicate dead code or incomplete implementation.

---

### Error 4: Unused Variable (VoiceCall.tsx:177)

**File:** `src/pages/VoiceCall.tsx`  
**Line:** 177  
**Issue:** Error parameter not used in catch block

**Current Code:**
```typescript
catch (e) {
  console.log('Error occurred');
}
```

**Fixed Code (Option A: Prefix with underscore):**
```typescript
catch (_e) {
  console.log('Error occurred');
}
```

**Fixed Code (Option B: Use the error):**
```typescript
catch (e) {
  console.error('Error occurred:', e);
}
```

**Why:** Unused parameters should be prefixed with underscore or used.

---

### Error 5: Unused ESLint Directive (VoiceCall.tsx:623)

**File:** `src/pages/VoiceCall.tsx`  
**Line:** 623  
**Issue:** ESLint disable comment has no effect

**Current Code:**
```typescript
// eslint-disable-next-line react-hooks/exhaustive-deps
// (no actual issue on the next line)
```

**Fixed Code:**
```typescript
// Remove the comment entirely
```

**Why:** Unused directives indicate the comment is no longer needed.

---

## 🟡 Warnings (Should Fix)

### Warning 1: Fast Refresh Export Issue (AuthContext.tsx:77)

**File:** `src/context/AuthContext.tsx`  
**Line:** 77  
**Issue:** File exports both components and constants

**Current Code:**
```typescript
export const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = () => {
  // hook implementation
};

export const AUTH_CONSTANTS = {
  // constants
};
```

**Fixed Code:**
```typescript
// AuthContext.tsx - only exports context and hook
export const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = () => {
  // hook implementation
};

// authConstants.ts - separate file for constants
export const AUTH_CONSTANTS = {
  // constants
};
```

**Why:** Fast refresh works better when files export only components/hooks.

---

### Warning 2: Missing Dependency (useVoiceChat.ts:363)

**File:** `src/hooks/useVoiceChat.ts`  
**Line:** 363  
**Issue:** useCallback missing dependency: 'stopAudioStream'

**Current Code:**
```typescript
const handleStop = useCallback(() => {
  stopAudioStream();
  // more code
}, []); // Missing stopAudioStream
```

**Fixed Code:**
```typescript
const handleStop = useCallback(() => {
  stopAudioStream();
  // more code
}, [stopAudioStream]); // Added dependency
```

**Why:** Missing dependencies can cause stale closures and bugs.

---

### Warning 3: Missing Dependency (RagManagement.tsx:45)

**File:** `src/pages/RagManagement.tsx`  
**Line:** 45  
**Issue:** useEffect missing dependency: 'selectedDealershipId'

**Current Code:**
```typescript
useEffect(() => {
  if (selectedDealershipId) {
    fetchDocuments(selectedDealershipId);
  }
}, []); // Missing selectedDealershipId
```

**Fixed Code:**
```typescript
useEffect(() => {
  if (selectedDealershipId) {
    fetchDocuments(selectedDealershipId);
  }
}, [selectedDealershipId]); // Added dependency
```

**Why:** Missing dependencies can cause effects to not run when they should.

---

### Warning 4: Missing Dependency (RagManagement.tsx:64)

**File:** `src/pages/RagManagement.tsx`  
**Line:** 64  
**Issue:** useEffect missing dependency: 'fetchStatus'

**Current Code:**
```typescript
useEffect(() => {
  if (fetchStatus === 'success') {
    // do something
  }
}, []); // Missing fetchStatus
```

**Fixed Code:**
```typescript
useEffect(() => {
  if (fetchStatus === 'success') {
    // do something
  }
}, [fetchStatus]); // Added dependency
```

**Why:** Missing dependencies can cause effects to not run when they should.

---

### Warning 5: Missing Dependency (UserManagement.tsx:58)

**File:** `src/pages/UserManagement.tsx`  
**Line:** 58  
**Issue:** useEffect missing dependency: 'loadUsers'

**Current Code:**
```typescript
useEffect(() => {
  loadUsers();
}, []); // Missing loadUsers
```

**Fixed Code:**
```typescript
useEffect(() => {
  loadUsers();
}, [loadUsers]); // Added dependency
```

**Why:** Missing dependencies can cause effects to not run when they should.

---

### Warning 6: Missing Dependencies (UserManagement.tsx:90)

**File:** `src/pages/UserManagement.tsx`  
**Line:** 90  
**Issue:** useEffect missing dependencies: 'isSuperAdmin' and 'loadUsers'

**Current Code:**
```typescript
useEffect(() => {
  if (isSuperAdmin) {
    loadUsers();
  }
}, []); // Missing both dependencies
```

**Fixed Code:**
```typescript
useEffect(() => {
  if (isSuperAdmin) {
    loadUsers();
  }
}, [isSuperAdmin, loadUsers]); // Added dependencies
```

**Why:** Missing dependencies can cause effects to not run when they should.

---

### Warning 7-9: Ref Cleanup Issues (VoiceCall.tsx:619-620)

**File:** `src/pages/VoiceCall.tsx`  
**Lines:** 619-620  
**Issue:** Ref values may change during cleanup

**Current Code:**
```typescript
useEffect(() => {
  return () => {
    clearTimeout(userTranscriptTimeoutRef.current);
    clearTimeout(avatarTranscriptTimeoutRef.current);
  };
}, []);
```

**Fixed Code:**
```typescript
useEffect(() => {
  const userTimeout = userTranscriptTimeoutRef.current;
  const avatarTimeout = avatarTranscriptTimeoutRef.current;
  
  return () => {
    if (userTimeout) clearTimeout(userTimeout);
    if (avatarTimeout) clearTimeout(avatarTimeout);
  };
}, []);
```

**Why:** Refs can change, so copy them to variables before using in cleanup.

---

## 📋 Step-by-Step Fix Process

### Step 1: Auto-Fix (5 minutes)
```bash
cd frontend
npm run lint -- --fix
```

### Step 2: Manual Fixes (30-45 minutes)

1. **Fix Case Blocks** (2 files)
   - Open `src/hooks/useVoiceChat.ts` line 286
   - Open `src/pages/VoiceChat.tsx` line 339
   - Wrap case blocks in braces

2. **Fix Unused Variables** (2 instances)
   - Open `src/pages/VoiceCall.tsx` line 95
   - Open `src/pages/VoiceCall.tsx` line 177
   - Remove or use variables

3. **Fix Missing Dependencies** (6 instances)
   - Open `src/hooks/useVoiceChat.ts` line 363
   - Open `src/pages/RagManagement.tsx` lines 45, 64
   - Open `src/pages/UserManagement.tsx` lines 58, 90
   - Add missing dependencies to arrays

4. **Fix Ref Cleanup** (1 instance)
   - Open `src/pages/VoiceCall.tsx` lines 619-620
   - Copy refs to variables before cleanup

5. **Fix Exports** (1 file)
   - Open `src/context/AuthContext.tsx`
   - Separate constants to different file

### Step 3: Verify (10 minutes)
```bash
npm run lint
npm run build
```

### Step 4: Test (15 minutes)
```bash
npm run dev
# Test in browser
```

---

## ✅ Verification Checklist

After making fixes, verify:

- [ ] `npm run lint` shows no errors
- [ ] `npm run build` completes successfully
- [ ] `npm run dev` starts without errors
- [ ] Application loads in browser
- [ ] All pages are accessible
- [ ] No console errors in browser DevTools

---

## 🎯 Priority Order

### Priority 1: Critical (Do First)
1. Fix case block declarations (2 files)
2. Remove unused variables (2 instances)
3. Remove unused directive (1 instance)

**Time:** 15-20 minutes

### Priority 2: Important (Do Second)
1. Add missing dependencies (6 instances)
2. Fix ref cleanup (1 instance)
3. Separate exports (1 file)

**Time:** 30-45 minutes

### Priority 3: Nice-to-Have (Optional)
1. Optimize bundle size
2. Implement code-splitting
3. Add more tests

**Time:** 1-2 hours

---

## 🚀 After Fixes

Once all fixes are complete:

```bash
# 1. Verify no errors
npm run lint

# 2. Build for production
npm run build

# 3. Test locally
npm run dev

# 4. Commit changes
git add .
git commit -m "fix: resolve ESLint errors and warnings"

# 5. Push to repository
git push origin main
```

---

## 📊 Expected Results After Fixes

```
Before:
  5 errors
  9 warnings
  ❌ Cannot deploy

After:
  0 errors
  0 warnings
  ✅ Ready to deploy
```

---

## 💡 Tips for Success

1. **Use VS Code ESLint Extension**
   - Install: ESLint extension
   - It will highlight issues in real-time
   - Use "Fix all auto-fixable problems" command

2. **Use TypeScript Strict Mode**
   - Helps catch more issues
   - Already enabled in tsconfig.json

3. **Test After Each Fix**
   - Run `npm run lint` after each file
   - Verify no new issues introduced

4. **Use Git to Track Changes**
   - Commit after each major fix
   - Easy to revert if needed

---

## 🆘 If You Get Stuck

### Issue: Can't find the line number
**Solution:** Use Ctrl+G in VS Code to go to line

### Issue: Don't understand the error
**Solution:** Read the error message carefully, it usually explains the issue

### Issue: Fix breaks something else
**Solution:** Use `git diff` to see what changed, revert if needed

### Issue: Still have errors after fixes
**Solution:** Run `npm run lint` again to see remaining issues

---

## 📞 Support

For questions about specific fixes:
1. Read the error message carefully
2. Check the examples in this document
3. Refer to React documentation: https://react.dev/
4. Check ESLint rules: https://eslint.org/docs/rules/

---

**Document Version:** 1.0  
**Last Updated:** February 7, 2026  
**Status:** Ready to use  
**Estimated Time to Complete:** 1-2 hours
