#!/bin/bash
rm -fr mongodb_dump.old
mkdir -p mongodb_dump
mongodb/bin/mongodump -d gkc
mv dump mongodb_dump

