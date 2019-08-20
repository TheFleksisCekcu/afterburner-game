#! /usr/bin/env python
# encoding: utf-8
# a1batross, mittorn, 2018

from __future__ import print_function
from waflib import Logs
import sys
import os

VERSION = '0.99'
APPNAME = 'xash3d-fwgs'
top = '.'

class Subproject:
	name      = ''
	dedicated = True  # if true will be ignored when building dedicated server
	singlebin = False # if true will be ignored when singlebinary is set
	ignore    = False # if true will be ignored, set by user request

	def __init__(self, name, dedicated=True, singlebin=False):
		self.name = name
		self.dedicated = dedicated
		self.singlebin = singlebin

SUBDIRS = [
	Subproject('public',      dedicated=False),
	Subproject('engine',      dedicated=False),
	Subproject('game_launch', singlebin=True),
	Subproject('ref_gl'),
#	Subproject('ref_soft'),
	Subproject('mainui'),
	Subproject('vgui_support'),
]

def subdirs():
	return map(lambda x: x.name, SUBDIRS)

def options(opt):
	grp = opt.add_option_group('Common options')

	grp.add_option('-T', '--build-type', action='store', dest='BUILD_TYPE', default = None,
		help = 'build type: debug, release or none(custom flags)')

	grp.add_option('-d', '--dedicated', action = 'store_true', dest = 'DEDICATED', default = False,
		help = 'build Xash Dedicated Server(XashDS)')

	grp.add_option('--single-binary', action = 'store_true', dest = 'SINGLE_BINARY', default = False,
		help = 'build single "xash" binary instead of xash.dll/libxash.so (forced for dedicated)')

	grp.add_option('-8', '--64bits', action = 'store_true', dest = 'ALLOW64', default = False,
		help = 'allow targetting 64-bit engine')

	grp.add_option('-W', '--win-style-install', action = 'store_true', dest = 'WIN_INSTALL', default = False,
		help = 'install like Windows build, ignore prefix, useful for development')

	grp.add_option('--enable-bsp2', action = 'store_true', dest = 'SUPPORT_BSP2_FORMAT', default = False,
		help = 'build engine and renderers with BSP2 map support(recommended for Quake, breaks compability!)')

	opt.load('subproject')

	opt.add_subproject(subdirs())

	opt.load('xcompile compiler_cxx compiler_c sdl2')
	if sys.platform == 'win32':
		opt.load('msvc msdev msvs')
	opt.load('reconfigure')


def configure(conf):
	conf.load('fwgslib reconfigure')
	conf.start_msg('Build type')
	if conf.options.BUILD_TYPE == None:
		conf.end_msg('not set', color='RED')
		conf.fatal('Please set a build type, for example "-T release"')
	elif not conf.options.BUILD_TYPE in ['fast', 'release', 'debug', 'nooptimize', 'sanitize', 'none']:
		conf.end_msg(conf.options.BUILD_TYPE, color='RED')
		conf.fatal('Invalid build type. Valid are "debug", "release" or "none"')
	conf.end_msg(conf.options.BUILD_TYPE)

	# -march=native should not be used
	if conf.options.BUILD_TYPE == 'fast':
		Logs.warn('WARNING: \'fast\' build type should not be used in release builds')

	conf.load('subproject')

	# Force XP compability, all build targets should add
	# subsystem=bld.env.MSVC_SUBSYSTEM
	# TODO: wrapper around bld.stlib, bld.shlib and so on?
	conf.env.MSVC_SUBSYSTEM = 'WINDOWS,5.01'
	conf.env.MSVC_TARGETS = ['x86'] # explicitly request x86 target for MSVC
	if sys.platform == 'win32':
		conf.load('msvc msvcfix msdev msvs')
	conf.load('xcompile compiler_c compiler_cxx gitversion clang_compilation_database')
	if sys.platform == 'win32':
		conf.load('msvc msvs')

	# Every static library must have fPIC
	if conf.env.DEST_OS != 'win32' and '-fPIC' in conf.env.CFLAGS_cshlib:
		conf.env.append_unique('CFLAGS_cstlib', '-fPIC')
		conf.env.append_unique('CXXFLAGS_cxxstlib', '-fPIC')

	# modify options dictionary early
	if conf.env.DEST_OS2 == 'android':
		conf.options.ALLOW64 = True # skip pointer length check
		conf.options.NO_VGUI = True # skip vgui
		conf.options.NANOGL = True
		conf.options.GLWES  = True
		conf.options.GL     = False

	# We restrict 64-bit builds ONLY for Win/Linux/OSX running on Intel architecture
	# Because compatibility with original GoldSrc
	if conf.env.DEST_OS in ['win32', 'linux', 'darwin'] and conf.env.DEST_CPU in ['x86_64']:
		conf.env.BIT32_ALLOW64 = conf.options.ALLOW64
		if not conf.env.BIT32_ALLOW64:
			Logs.info('WARNING: will build engine for 32-bit target')
	else:
		conf.env.BIT32_ALLOW64 = True
	conf.env.BIT32_MANDATORY = not conf.env.BIT32_ALLOW64
	conf.load('force_32bit')
	if conf.env.DEST_OS2 != 'android' and not conf.options.DEDICATED:
		conf.load('sdl2')

	linker_flags = {
		'common': {
			'msvc':    ['/DEBUG', '/WX'], # always create PDB, doesn't affect result binaries
			'gcc': ['-Wl,--no-undefined']
		},
		'sanitize': {
			'clang':   ['-fsanitize=undefined', '-fsanitize=address'],
			'gcc':     ['-fsanitize=undefined', '-fsanitize=address'],
		}
	}

	compiler_c_cxx_flags = {
		'common': {
			# disable thread-safe local static initialization for C++11 code, as it cause crashes on Windows XP
			'msvc':    ['/D_USING_V110_SDK71_', '/Zi', '/FS', '/Zc:threadSafeInit-', '/MT', '/WX'],
			'clang': [
				'-g',
				'-gdwarf-2',
				'-Werror',
				'-fvisibility=hidden',
			],
			'gcc': [
				'-g',
				'-fdiagnostics-color=always',
				'-Werror',
				'-fvisibility=hidden',
			]
		},
		'fast': {
			'msvc':    ['/O2', '/Oy'], #todo: check /GL /LTCG
			'gcc':     ['-Ofast', '-march=native', '-funsafe-math-optimizations', '-funsafe-loop-optimizations', '-fomit-frame-pointer'],
			'clang':   ['-Ofast', '-march=native'],
			'default': ['-O3']
		},
		'release': {
			'msvc':    ['/O2', '/DNDEBUG'],
			'default': ['-O3', '-DNDEBUG']
		},
		'debug': {
			'msvc':    ['/O1', '/D_DEBUG'],
			'gcc':     ['-Og', '-D_DEBUG'],
			'default': ['-O1', '-D_DEBUG']
		},
		'sanitize': {
			'msvc':    ['/Od', '/RTC1'],
			'gcc':     ['-Og', '-fsanitize=undefined', '-fsanitize=address'],
			'clang':   ['-O0', '-fsanitize=undefined', '-fsanitize=address'],
			'default': ['-O0']
		},
		'nooptimize': {
			'msvc':    ['/Od'],
			'default': ['-O0']
		}
	}

	conf.env.append_unique('CFLAGS', conf.get_flags_by_type(
		compiler_c_cxx_flags, conf.options.BUILD_TYPE, conf.env.COMPILER_CC))
	conf.env.append_unique('CXXFLAGS', conf.get_flags_by_type(
		compiler_c_cxx_flags, conf.options.BUILD_TYPE, conf.env.COMPILER_CC))
	conf.env.append_unique('LINKFLAGS', conf.get_flags_by_type(
		linker_flags, conf.options.BUILD_TYPE, conf.env.COMPILER_CC))

	conf.env.DEDICATED     = conf.options.DEDICATED
	# we don't need game launcher on dedicated
	conf.env.SINGLE_BINARY = conf.options.SINGLE_BINARY or conf.env.DEDICATED
	if conf.env.DEST_OS == 'linux':
		conf.check_cc( lib='dl' )

	if conf.env.DEST_OS != 'win32':
		if conf.env.DEST_OS2 != 'android':
			conf.check_cc( lib='m' ) # HACK: already added in xcompile!
			conf.check_cc( lib='pthread' )
	else:
		# Common Win32 libraries
		# Don't check them more than once, to save time
		# Usually, they are always available
		# but we need them in uselib
		conf.check_cc( lib='user32' )
		conf.check_cc( lib='shell32' )
		conf.check_cc( lib='gdi32' )
		conf.check_cc( lib='advapi32' )
		conf.check_cc( lib='dbghelp' )
		conf.check_cc( lib='psapi' )
		conf.check_cc( lib='ws2_32' )


	# indicate if we are packaging for Linux/BSD
	if(not conf.options.WIN_INSTALL and
		conf.env.DEST_OS not in ['win32', 'darwin'] and
		conf.env.DEST_OS2 not in ['android']):
		conf.env.LIBDIR = conf.env.BINDIR = '${PREFIX}/lib/xash3d'
	else:
		conf.env.LIBDIR = conf.env.BINDIR = conf.env.PREFIX

	conf.env.append_unique('DEFINES', 'XASH_BUILD_COMMIT="{0}"'.format(conf.env.GIT_VERSION if conf.env.GIT_VERSION else 'notset'))
	conf.env.append_unique('DEFINES', 'AFTERBURNER_ENGINE')

	for i in SUBDIRS:
		if conf.env.SINGLE_BINARY and i.singlebin:
			continue

		if conf.env.DEST_OS2 == 'android' and i.singlebin:
			continue

		if conf.env.DEDICATED and i.dedicated:
			continue

		conf.add_subproject(i.name)

def build(bld):
	for i in SUBDIRS:
		if bld.env.SINGLE_BINARY and i.singlebin:
			continue

		if bld.env.DEST_OS2 == 'android' and i.singlebin:
			continue

		if bld.env.DEDICATED and i.dedicated:
			continue

		bld.add_subproject(i.name)
