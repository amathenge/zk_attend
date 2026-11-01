drop table if exists log;

create table log (
    id integer primary key autoincrement,
    logdate datetime not null default CURRENT_TIMESTAMP,
    user integer not null,
    log text
);

