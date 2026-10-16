/* Minimal regex.h stub for Windows host builds (winlibs UCRT has no
 * POSIX regex).
 *
 * scripts/kconfig/symbol.c uses regcomp/regexec for the interactive
 * symbol search in menuconfig. That code path is never reached by
 * defconfig/oldconfig/syncconfig builds, so a stub that reports
 * "invalid pattern" degrades gracefully (search returns no match)
 * without affecting kernel configuration generation.
 *
 * Found via -I scripts/include (scripts/Makefile.host always adds it).
 */
#ifndef _KCONFIG_WIN_REGEX_STUB_H
#define _KCONFIG_WIN_REGEX_STUB_H

#include <stddef.h>

typedef struct regex_t { int _unused; } regex_t;
typedef struct regmatch_t { int rm_so; int rm_eo; } regmatch_t;

#define REG_EXTENDED 1
#define REG_ICASE    2
#define REG_NEWLINE  4
#define REG_NOTBOL   8
#define REG_NOTEOL   16
#define REG_NOMATCH  1

static inline int regcomp(regex_t *re, const char *pattern, int flags)
{
	(void)re; (void)pattern; (void)flags;
	return -1; /* always "invalid pattern" */
}

static inline int regexec(const regex_t *re, const char *s, size_t nmatch,
			  regmatch_t pmatch[], int flags)
{
	(void)re; (void)s; (void)nmatch; (void)pmatch; (void)flags;
	return REG_NOMATCH;
}

static inline void regfree(regex_t *re)
{
	(void)re;
}

#endif /* _KCONFIG_WIN_REGEX_STUB_H */
