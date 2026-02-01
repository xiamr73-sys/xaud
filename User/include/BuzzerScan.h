/**************************** (C) COPYRIGHT 2015 Fortiortech shenzhen *****************************
* File Name          : BuzzerScan.h
* Author             : Billy Long Fortiortech  Market Dept
* Version            : V1.0
* Date               : 01/07/2015
* Description        : This file contains all the common data types used for Motor Control.
***************************************************************************************************
* All Rights Reserved
**************************************************************************************************/ 

/* Define to prevent recursive inclusion --------------------------------------------------------*/
#ifndef __BUZZERSCAN_H_
#define __BUZZERSCAN_H_

#include "FU68xx_4_MCU.h"

/*BUZZER */
#define		BuzzerRingFrq											(4000)

/* Exported types -------------------------------------------------------------------------------*/
typedef struct
{	
	uint8	FlagBZ;
	uint8	BZRunTime;
	uint16	BZCnt;
	uint8	BZMultitimes;
	uint16	BZMultitimesCount;
} BZScan_TypeDef;

/* Exported variables ---------------------------------------------------------------------------*/
//extern BZScan_TypeDef xdata BZScan;

/* Exported functions ---------------------------------------------------------------------------*/
extern void BuzzerInit(void);
extern void SetBuzzer(uint8 BZRunTime,uint8 BZMultitimes);
extern void BuzzerScan(void);

#endif

