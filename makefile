
include userconfig.mk

PACKET=bin/$(NAME).sh
MAIN=src/$(NAME).py

$(PACKET): $(MAIN)
	@mkdir -p bin/
	npyck -a $(MAIN) $(INCLUDE) -o $(PACKET)

all: $(PACKET)

.PHONY: clean git-clean run packet expand

git-clean: clean
#	rm -f *~ */*~
	@find . -name \*~
	find . -name \*~ -exec rm "{}" ";"
	@find . -name \*.pyc
	find . -name \*.pyc -exec rm "{}" ";"

expand:
	expand --tabs=4 $(MAIN) >make.tmp
	cp make.tmp $(MAIN)
	rm make.tmp

clean:
	rm -fr ./bin/

run:
	python $(MAIN) $(ARGS)

packet: $(PACKET)
	sh $(PACKET)
