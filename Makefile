.PHONY: setup native test

setup:
	python3 -m venv .venv
	.venv/bin/pip install -r requirements.txt
	$(MAKE) native

native:
	mkdir -p bin
	mkdir -p .build/clang-modules .build/swift-modules
	CLANG_MODULE_CACHE_PATH=$(CURDIR)/.build/clang-modules SWIFT_MODULECACHE_PATH=$(CURDIR)/.build/swift-modules swiftc extract.swift -o bin/extract -framework Foundation -framework AppKit -framework PDFKit -framework AVFoundation -framework Vision -framework ImageIO
	CLANG_MODULE_CACHE_PATH=$(CURDIR)/.build/clang-modules SWIFT_MODULECACHE_PATH=$(CURDIR)/.build/swift-modules swiftc dashboard_service/trash.swift -o bin/trash -framework Foundation -framework AppKit

test:
	PYTHONPYCACHEPREFIX=/tmp/file-library-organizer-pyc .venv/bin/python tests/test_organizer.py
	PYTHONPYCACHEPREFIX=/tmp/file-library-organizer-pyc .venv/bin/python dashboard_service/test_actions.py
