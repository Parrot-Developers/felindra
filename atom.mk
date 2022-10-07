
LOCAL_PATH := $(call my-dir)

###############################################################################
# felindra
###############################################################################

include $(CLEAR_VARS)

LOCAL_MODULE := felindra
LOCAL_DESCRIPTION := Parrot Media Signature Verifier tool
LOCAL_CATEGORY_PATH := tools
LOCAL_LIBRARIES := \
	python

FELINDRA_MODULE_NAME = felindra
LOCAL_SRC_FILES := $(call all-files-under,src/$(FELINDRA_MODULE_NAME),.py)
FELINDRA_MAIN_FILE := bin/$(FELINDRA_MODULE_NAME).py
FELINDRA_WHEEL_FILES := \
	src/$(FELINDRA_MODULE_NAME)/__init__.py \
	src/$(FELINDRA_MODULE_NAME)/__main__.py

FELINDRA_LIBRARY_FILES := $(filter-out $(FELINDRA_MAIN_FILE) $(FELINDRA_WHEEL_FILES), \
	$(LOCAL_SRC_FILES))
FELINDRA_SHARE_FILES := $(call all-files-under,src/$(FELINDRA_MODULE_NAME)/etc/share,*)
LOCAL_COPY_FILES := \
	$(FELINDRA_MAIN_FILE):usr/bin/$(LOCAL_MODULE) \
	$(FELINDRA_LIBRARY_FILES:=:usr/lib/python/site-packages/$(LOCAL_MODULE)/) \
	$(FELINDRA_SHARE_FILES:=:usr/share/$(LOCAL_MODULE)/) \

include $(BUILD_CUSTOM)

###############################################################################
# felindra-wheel
###############################################################################

include $(CLEAR_VARS)

LOCAL_MODULE := felindra-wheel
LOCAL_CATEGORY_PATH := libs
LOCAL_DESCRIPTION := felindra wheel package
LOCAL_DEPENDS_MODULES := \
	felindra

LOCAL_COPY_TO_BUILD_DIR := 1
LOCAL_COPY_TO_BUILD_DIR_SKIP_FILES := ".mypy_cache/*"

FELINDRA_DEB_BUILD_DIR := $(call local-get-build-dir)

define LOCAL_CMD_BUILD
	@( \
		cd $(FELINDRA_DEB_BUILD_DIR)/; \
		python3 -m poetry version $(PARROT_BUILD_PROP_VERSION); \
		python3 -m poetry install; \
		python3 -m poetry build; \
		python3 -m poetry version 0.0.0 \
	)
endef

include $(BUILD_CUSTOM)
