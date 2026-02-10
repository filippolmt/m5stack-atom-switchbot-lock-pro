.PHONY: test test-build test-clean

IMAGE_NAME := switchbot-firmware-tests

test-build:
	docker build -f Dockerfile.test -t $(IMAGE_NAME) .

test: test-build
	docker run --rm $(IMAGE_NAME)

test-clean:
	docker rmi $(IMAGE_NAME) 2>/dev/null || true
