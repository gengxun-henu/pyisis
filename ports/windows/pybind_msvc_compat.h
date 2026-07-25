// Copyright (c) 2026 Geng Xun, Henan University
// SPDX-License-Identifier: MIT
//
// Purpose: Establish Windows SDK declarations before ISIS CSPICE headers
// define compatibility macros such as VOID.

#pragma once

#if defined(_WIN32) && defined(_MSC_VER)
#  ifndef NOMINMAX
#    define NOMINMAX
#  endif
#  ifndef WIN32_LEAN_AND_MEAN
#    define WIN32_LEAN_AND_MEAN
#  endif
#  ifndef NOGDI
#    define NOGDI
#  endif

#  define Ellipse WindowsSdkEllipse
#  include <windows.h>
#  undef Ellipse

#  ifdef DIFFERENCE
#    undef DIFFERENCE
#  endif
#  ifdef near
#    undef near
#  endif
#  ifdef far
#    undef far
#  endif
#endif
