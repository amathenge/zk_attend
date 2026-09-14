drop table if exists users;

create table users (
    id integer primary key,
    email varchar(32) not null unique,
    password varchar(256),
    firstname varchar(16) not null,
    lastname varchar(16) not null,
    phone varchar(16) not null,
    auth varchar(8) not null default '0'
);

.read sql/user_data.sql
