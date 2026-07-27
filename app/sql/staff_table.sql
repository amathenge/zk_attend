-- user table
drop table if exists staff;

create table staff (
    id integer primary key,
    staff varchar(16) not null,
    firstname varchar(16) not null,
    surname varchar(16) not null,
    active integer not null default 1 check (active in (0, 1))
);

.read sql/staff.sql