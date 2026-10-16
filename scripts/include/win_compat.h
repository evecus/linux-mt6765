/* Windows (winlibs UCRT) host-build compatibility shim.
 *
 * The winlibs MinGW-w64 UCRT toolchain has two host-build gaps:
 *
 *  1. <string.h> does not expose strndup(), used by kernel host tools
 *     (scripts/include/xalloc.h, scripts/dtc/util.c, ...).
 *  2. The UCRT defaults _fmode to _O_TEXT: open() without O_BINARY
 *     translates CRLF on read, so read() returns fewer bytes than
 *     st_size -> scripts/basic/fixdep fails with "read: No error".
 *     Same hazard for scripts/dtc reading binary .dtb files.
 *
 * Force-included via HOSTCFLAGS="-include win_compat.h"; fixes the
 * build without touching kernel sources.
 */
#ifndef _WIN_COMPAT_H
#define _WIN_COMPAT_H

#include <string.h>
#include <stdlib.h>
#include <stdio.h>
#include <sys/types.h>

/*
 * strndup()/getline(): not declared AND not exported by the winlibs
 * UCRT runtime -> provide inline implementations.
 */
#if defined(_WIN32) && !defined(WIN_COMPAT_HAVE_STRNDUP)
#define WIN_COMPAT_HAVE_STRNDUP
static inline char *strndup(const char *s, size_t n)
{
	size_t len = 0;
	char *p;

	while (len < n && s[len])
		len++;
	p = malloc(len + 1);
	if (!p)
		return NULL;
	memcpy(p, s, len);
	p[len] = '\0';
	return p;
}
#endif

#if defined(_WIN32) && !defined(WIN_COMPAT_HAVE_GETLINE)
#define WIN_COMPAT_HAVE_GETLINE
static inline ssize_t getline(char **lineptr, size_t *n, FILE *stream)
{
	size_t len = 0;
	int c;

	if (!lineptr || !n || !stream)
		return -1;
	if (!*lineptr) {
		*n = 128;
		*lineptr = malloc(*n);
		if (!*lineptr)
			return -1;
	}
	while ((c = getc(stream)) != EOF) {
		if (len + 2 > *n) {
			size_t nn = *n * 2;
			char *np = realloc(*lineptr, nn);

			if (!np)
				return -1;
			*lineptr = np;
			*n = nn;
		}
		(*lineptr)[len++] = (char)c;
		if (c == '\n')
			break;
	}
	if (len == 0)
		return -1;
	(*lineptr)[len] = '\0';
	return (ssize_t)len;
}
#endif

#ifndef strchrnul
static inline char *strchrnul(const char *s, int c)
{
	char *p = strchr(s, c);

	return p ? p : (char *)s + strlen(s);
}
#endif

#ifdef _WIN32
#include <fcntl.h>
#include <io.h>
#include <stdio.h>
#include <direct.h>

/* POSIX mkdir(path, mode) -> Windows _mkdir(path); mode is meaningless
 * on Windows and swallowed by the variadic macro. */
#define mkdir(path, ...) _mkdir(path)
/* Force binary mode for every host tool that includes this header:
 * - _set_fmode() covers future open() calls (fixdep reading .cmd/.d,
 *   dtc reading binary .dtb, ...)
 * - _setmode(stdout) covers the stdout the CRT already opened in text
 *   mode at startup, which would otherwise turn every "\n" printf into
 *   CRLF and break .cmd consumers (fixdep's own parser among them).
 */
static void _wincompat_init_fmode(void) __attribute__((constructor));
static void _wincompat_init_fmode(void)
{
	_set_fmode(_O_BINARY);
	_setmode(_fileno(stdout), _O_BINARY);
	_setmode(_fileno(stderr), _O_BINARY);
}
#endif

#endif /* _WIN_COMPAT_H */
