
include userconfig.mk

PACKET=bin/$(NAME).sh
SOURCE=src/$(NAME).py

$(PACKET): $(SOURCE)
	@mkdir -p bin/
	npyck -a $(SOURCE) $(INCLUDE) -o $(PACKET)

all: $(PACKET)

.PHONY: clean git-clean run packet

git-clean: clean
#	rm -f *~ */*~
	make clean
	@find . -name \*~
	find . -name \*~ -exec rm "{}" ";"
	@find . -name \*.pyc
	find . -name \*.pyc -exec rm "{}" ";"

clean:
	rm -fr ./bin/

run:
	python $(SOURCE) $(ARGS)

packet: $(PACKET)
	sh $(PACKET)
