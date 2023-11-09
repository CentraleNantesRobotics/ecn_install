#!/usr/bin/env bash

ldapsearch -x -H ldaps://rldap.ec-nantes.fr -D "okermorg@ec-nantes.fr" -W -b "dc=rldap,dc=ec-nantes,dc=fr" cn
