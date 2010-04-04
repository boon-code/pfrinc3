
include userconfig.mk

PACKET=$(NAME).sh
SOURCE=$(NAME).py

$(PACKET): $(SOURCE)
	mkdir ./bin/
	npyck -a $(SOURCE) ./cfg/config.txt -o ./bin/$(PACKET)

all: $(TARGET)

.PHONY: clean git-clean test

git-clean: clean
#	rm -f *~ */*~
	make clean
	@find . -name \*~
	find . -name \*~ -exec rm "{}" ";"
	@find . -name \*.pyc
	find . -name \*.pyc -exec rm "{}" ";"

clean:
	rm -fr ./bin/

test:
	./src/pfserver.py ./cfg/config.txt
