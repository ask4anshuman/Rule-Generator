BEGIN
loader.persist_rules(
created_by => 'abc@df.com',
comments => 'Sample rules',
rules => rules(
               rule('PROCESS','OPERATION','@PROCESS.SOURCE_PARAM','DEFAULTVALUE'),
               rule('PROCESS','OPERATION','[CONTAINER]%[ACTION]','APPEND'),
               rule('PROCESS','OPERATION','[CONTAINER]%[SOURCE]',
                   q'[SELECT COL_A, COL_B, COL_C
                      FROM DUAL WHERE COL_C = @PROCESS.SOURCE_PARAM]'),
               rule('PROCESS','OPERATION','[CONTAINER]','target_table'),
               rule('PROCESS','OPERATION','[CONTAINER].[COL_A]','COL_A'),
               rule('PROCESS','OPERATION','[CONTAINER].[COL_B]','COL_B'),
               rule('PROCESS','OPERATION','[CONTAINER].[COL_C]','COL_C')
));
END;
/
SHOW USER;
