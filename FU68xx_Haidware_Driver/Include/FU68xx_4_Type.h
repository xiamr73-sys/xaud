/*  -------------------------- (C) COPYRIGHT 2020 Fortiortech ShenZhen ---------------------------*/
/*  File Name      : FU68xx_4_Type.h
/*  Author         : Fortiortech  Appliction Team
/*  Version        : V1.0
/*  Date           : 2020-08-24
/*  Description    : This file contains XX-XX-XX parameter used for Motor Control.
/*  ----------------------------------------------------------------------------------------------*/
/*                                     All Rights Reserved
/*  ----------------------------------------------------------------------------------------------*/

/*  Define to prevent recursive inclusion --------------------------------------------------------*/
#ifndef __FU68XX_4__TYPE_H_
#define __FU68XX_4__TYPE_H_

#define _I                              volatile const
#define _O                              volatile
#define _IO                             volatile

#define bool                            bit
#define false                           (0)
#define true                            (1)

typedef unsigned char                   uint8;
typedef unsigned short                  uint16;
typedef unsigned long                   uint32;
typedef long                            int32;
typedef short                           int16;
typedef char                            int8;

//typedef enum{false = 0, true = 1}       bool;
typedef enum{DISABLE = 0, ENABLE}       ebool;

#endif
