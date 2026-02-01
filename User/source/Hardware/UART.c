/*  --------------------------- (C) COPYRIGHT 2020 Fortiortech ShenZhen -----------------------------
    File Name      : UART.c
    Author         : Fortiortech  Appliction Team
    Version        : V1.0
    Date           : 2020-04-11
    Description    : This file contains .C file function used for Motor Control.
    ----------------------------------------------------------------------------------------------------
                                       All Rights Reserved
    ------------------------------------------------------------------------------------------------- */
#include <FU68xx_2.h>
#include "Myproject.h"

MCUART Uart;
SELFLEARN Learn;
SELFLEARN Power;
UART_FLAG xdata UARTFL;
extern int32  speedRef;
uint8 Flash_Data[6]={0};

//extern  uint16 xdata Speed_Level_flag;
//extern bit Count1s_flag;
//extern uint32 xdata Time_Keep;
bit Control_ture = 0;
bit  Send_Overflag = 1;
bit uatr1s_flag = 0;
float MinAngleLim = 34.0;
float MaxAngleLim = 234.0;


uint16 MinAngleCode  = (0x2FA << 2); //306
uint16 MaxAngleCode  = (0x14D9 << 2); //14CD
uint16 MiddleAngleCode  = (0x0BE9 << 2);

uint16 lightSwitch  = (0x1467 << 2);

/*  ----------------------------------------------------------------------------------------------*/
/*  Function Name  : UART2_Init
    /*  Description    : UART2_Init
    /*  Date           : 2020-09-06
    /*  Parameter      : None
    /*  ----------------------------------------------------------------------------------------------*/
void UART2_Init(void)
{
    SetBit(PH_SEL, UART2EN);    //P3[6]as UART2_RXD; P3[7]as UART2_TXD
    #if 0
    ClrBit(P3_OE, P36);         //输入使能
    SetBit(P3_PU, P36);         //上拉电阻
    SetBit(P3_OE, P37);         //输出使能
    SetBit(P3_PU, P37);         //上拉电阻
    #endif
    ClrBit(UT2_CR, UT2MOD1);    //00-->单线制8bit        01-->8bit uart(波特率可设置)
    SetBit(UT2_CR, UT2MOD0);    //10-->单线制9bit        11-->9bit uart(波特率可设置)
    ClrBit(UT2_CR, UT2SM2);     //0-->单机通讯          1-->多机通讯；
    //    SetBit(UT2_CR, UT2REN);     //0-->不允许串行输入 1-->允许串行输入，软件清0;
    ClrBit(UT2_CR, UT2TB8);     //模式2/3下数据发送第9位，在多机通信中，可用于判断当前数据帧的数据是地址还是数据，TB8=0为数据，TB8=1为地址
    ClrBit(UT2_CR, UT2RB8);     //模式2/3下数据接收第9位，若SM2=0,作为停止位
    ClrBit(UT2_CR, UT2TI);
    ClrBit(UT2_CR, UT2RI);
    SetBit(UT2_CR, UT2REN);     //0-->不允许串行输入 1-->允许串行输入，软件清0;
    PSPI_UT21 = 0;              //中断优先级时最低
    PSPI_UT20 = 0;
    UT2_BAUD = 0x9B;      //波特率可设置 = 24000000/(16/(1+ UT_BAUD[BAUD_SEL]))/(UT_BAUD+1)
    //9B-->9600 0x000c-->115200 0x0005-->256000  4800-0x137;2400-0x270;1200-0x4E1
    ClrBit(UT2_BAUD, BAUD2_SEL); //倍频使能0-->Disable  1-->Enable
    SetBit(UT2_BAUD, UART2CH);   //UART2端口功能转移使能0：P36->RXD P37->TXD 1:P01->RXD P00->TXD
    SetBit(UT2_BAUD, UART2IEN);  //UART2中断使能0-->Disable  1-->Enable
}


/*  ----------------------------------------------------------------------------------------------*/
/*  Function Name  : UART1_Init
    /*  Description    : UART1_Init
    /*  Date           : 2020-09-06
    /*  Parameter      : None
    /*  ----------------------------------------------------------------------------------------------*/
void UART1_Init(void)
{
    SetBit(PH_SEL, UART1EN);    //P0[6]as UART2_RXD; P0[5]as UART2_TXD
    #if 0
    ClrBit(P0_OE, P06);         //输入使能
    SetBit(P0_PU, P06);         //上拉电阻
    SetBit(P0_OE, P05);         //输出使能
    SetBit(P0_PU, P05);         //上拉电阻
    #endif
    UT_MOD1 = 0;    //00-->单线制8bit        01-->8bit uart(波特率可设置)
    UT_MOD0 = 1;    //10-->单线制9bit        11-->9bit uart(波特率可设置)
    SM2 = 0;        //0-->单机通讯          1-->多机通讯；
    REN = 1;        //0-->不允许串行输入 1-->允许串行输入，软件清0;
    TB8 = 0;        //模式2/3下数据发送第9位，在多机通信中，可用于判断当前数据帧的数据是地址还是数据，TB8=0为数据，TB8=1为地址
    RB8 = 0;        //模式2/3下数据接收第9位，若SM2=0,作为停止位
    PI2C_UT11 = 0;                 //中断优先级时最低
    PI2C_UT10 = 0;
    ClrBit(UT_BAUD, UART_2xBAUD);   //倍频使能0-->Disable  1-->Enable
    ES0 = 0;                        //UART1中断使能0-->Disable  1-->Enable
    UT_BAUD = 0x009B;//波特率可设置 = 24000000/(16/(1+ UT_BAUD[BAUD_SEL]))/(UT_BAUD+1)
    //9B-->9600 0x000c-->115200
}

float spd;
extern int16 Speed_lim;

uint8 PosErrSET;

void Speed_Handle(uint8 level)
{
    if (level >= 0x90)
    {
        level = 0x90;
    }
    else if (level <= 0x00)
    {
        level = 0x00;
    }
    
    //  spd = level * 0.75 + 2; //rpm ->°/s //0.82*level+0.333
    spd = level * 0.83 + 0.333;
    Uart.Speed_Level = level;
    mcSpeedRampLim.IncValue = 60;
    mcSpeedRampLim.DecValue = 60;
 
    /***********************每次设定速度限制时重新规划曲线**********************/
    mcFocCtrl.SpeedRefLim = S_Value(spd);
    mcSpeedRampLim.TargetValue = S_Value(spd);
    //
    mcSpeedRampLim.ActualValue  = 0;
    mcSpeedRampLim.ActualValueFlt  = 0;
    mcSpeedRampLim.ActualValueFlt_LSB = 0;
}


void UartTxdate(uint16 * sndBuf, int32 len)
{
    uint16 i = 0;
    
    for (i = 0; i < len; i++)
    {
        UART_SendData(*sndBuf++);
    }
}
void UART_SendData(unsigned char T_Data)
{
//	Wait_DMA(1);
//	
//	DMA1_LEN=Uart.T_Len-1;
//		Switch_DMA(1);
	
    UT2_DR = T_Data;
    
    while (!(ReadBit(UT2_CR, UT2TI)));     //等待发送完成
   
        TI = 0;                 //发送完成中断标志位清零
}

void Send_NoActive(void) //无效指令
{
    Uart.T_DATA[0] = 0x90;
    Uart.T_DATA[1] = 0x51;
    Uart.T_DATA[2] = 0xFF;
    Uart.SendCnt = 0;
    Uart.T_Len = 3;
    UART_SendData(Uart.T_DATA[0]);
}

void Send_ACK(void)
{
    Uart.T_DATA[0] = 0x90;
    Uart.T_DATA[1] = 0x40;
    Uart.T_DATA[2] = 0xFF;
    Uart.SendCnt = 0;
    Uart.T_Len = 3;
    UART_SendData(Uart.T_DATA[0]);
}

void Send_Success(void)
{
    Uart.T_DATA[0] = 0x90;
    Uart.T_DATA[1] = 0x50;
    Uart.T_DATA[2] = 0xFF;
    Uart.SendCnt = 0;
    Uart.T_Len = 3;
    UART_SendData(Uart.T_DATA[0]);
}

void Send_Fail(void)
{
    Uart.T_DATA[0] = 0x90;
    Uart.T_DATA[1] = 0x60;
    Uart.T_DATA[2] = 0x41;
    Uart.T_DATA[3] = 0xFF;
    Uart.SendCnt = 0;
    Uart.T_Len = 4;
    UART_SendData(Uart.T_DATA[0]);
}



/***************处理串口发送的数据************/
void UartDealResponse(void)
{
    Uart.T_DATA[0] = 0x90;
    Uart.T_DATA[1] = 0x50;
    Uart.T_DATA[Uart.T_Len - 1] = 0xFF;
    Uart.SendCnt = 0;
    UART_SendData(Uart.T_DATA[0]);
}




uint8 singal = 0;

int16 DelataWithSpeed = 0;
int16 VToalDelat;

uint8 TimeTounch ;

void StopCurve(void)
{

}


extern int32 PosErr;

/***************处理串口接收到的数据************/
uint16  Coordinate = 0;
uint16  CoordinateLast = 0;

uint16  PosiAngle = 0;
uint32  PosiAngleSum = 0;


int16 TempBaisL = 0;
int16 TempBaisR = 0;
int16 TempBaisWidth = 0;

uint8 TurnDir = 0x00;

void UartDealComm(void)
{
     if (Uart.ResponceFlag == 1)
    {
        switch (Uart.R_DATA[1])
        {            
            case 0x02:
                switch (Uart.R_DATA[2])
                {
                    case 0x38:                        
                        
                        Uart.T_DATA[0] = 0x90;
                        Uart.T_DATA[1] = 0x50;
                        Uart.T_DATA[2] = 0x01;
                        Uart.T_DATA[3] = 0x00;
                  
                        Uart.T_Len = 5;
                        Uart.RxFSM = 1;
                        
                        break;
                    
                }
                break;
        }
        if (Uart.RxFSM == 1)
        {
            UartDealResponse();
            Uart.RxFSM = 0;
        }
        Uart.ResponceFlag = 0;
    }
}


void UartDealComm2(void)
{
    if (Uart.ResponceFlag == 1)
    {

        switch (Uart.R_DATA[1])
        {
            case 0x01:
            
                /**********************直接回复ACK************************/
                Send_ACK();
				        Uart.RxFSM = 1;
                switch (Uart.R_DATA[3])
                {
                    case 0x01:
                        if ((Uart.R_DATA[5]  == 0x05) && (Uart.R_DATA[6]  == 0x05))
                        {
                            MOE = 0;
                            GP44 = 1;
                        }
                        else if ((Uart.R_DATA[5]  == 0x06) && (Uart.R_DATA[6]  == 0x06))
                        {
                            GP44 = 1;
                            SetBit(RST_SR , SOFTR);
                            MOE = 1;
                        }
                        break;
                    case 0x02://单圈位置闭环控制命令81 01 06 02 XX 0V 0V 0V 0V 02 03 FF
												Speed_Handle(Uart.R_DATA[4]);
                        PosiAngle = (Uart.R_DATA[5] << 12) + (Uart.R_DATA[6] << 8) + (Uart.R_DATA[7] << 4) + Uart.R_DATA[8];
                        mcQEP.ZSaveFlag = 0;
												UqPo.UqPoaiFlag = 0;
												UqPo.UqPosiLockFlag = 1;
												mcFocCtrl.ThetaIQ_SOURCE = 0;
                        if ((Uart.R_DATA[9]  == 0x03) && (Uart.R_DATA[10]  == 0x02))
                        {
                            mcSP.PulsesNum =  (PosiAngle) + mcQEP.ZeroCntr + mcQEP.ZeroNewCntr;
                            if (mcSP.PulsesNum < mcQEP.CntrSumReal - 20)
                            {
                                mcSP.PulsesNum += 65536;
                            }
														if(Uart.R_DATA[5] == 0x03)
														{
															UARTFL.flag_90 = 1;
														}
														else if(Uart.R_DATA[5] == 0x07)
														{
															UARTFL.flag_180 = 1;
														}
														else if(Uart.R_DATA[5] == 0x0B)
														{
															UARTFL.flag_270 = 1;
														}
														else if(Uart.R_DATA[5] == 0x0F)
														{
															UARTFL.flag_0 = 1;
														}
                        }
                        else if ((Uart.R_DATA[10]  == 0x03) && (Uart.R_DATA[9]  == 0x02))
                        {
                            mcSP.PulsesNum = -(65536 -(int32)(PosiAngle)) + mcQEP.ZeroCntr + mcQEP.ZeroNewCntr; //4096线*4 = 16383 = 一圈，反转
                            if (mcSP.PulsesNum > mcQEP.CntrSumReal + 20)
                            {
                                mcSP.PulsesNum -= 65536;
                            }
                        }
                        
                        //Speed_Handle(Uart.R_DATA[4]);
                        break;
                        
                    case 0x03://增量位置闭环控制命令
                        Speed_Handle(Uart.R_DATA[4]);
                        PosiAngleSum = (int32)(((int32)Uart.R_DATA[5] << 28) + ((int32)Uart.R_DATA[6] << 24) + ((int32)Uart.R_DATA[7] << 20) + ((int32)Uart.R_DATA[8] << 16)+ ((int32)Uart.R_DATA[9] << 12)+ ((int32)Uart.R_DATA[10] << 8)+ ((int32)Uart.R_DATA[11] << 4) + (int32)Uart.R_DATA[12]);
                        
                        //Speed_Handle(Uart.R_DATA[4]);
                        if ((Uart.R_DATA[9]  == 0x02) && (Uart.R_DATA[10]  == 0x03))
                        {
                            mcSP.PulsesNum =  mcQEP.CntrSumReal - (PosiAngleSum >> 2);
                        }
                        else if ((Uart.R_DATA[10]  == 0x02) && (Uart.R_DATA[9]  == 0x03))
                        {
                            mcSP.PulsesNum =  mcQEP.CntrSumReal + (PosiAngleSum >> 2);
                        }
                        
                        break;
                        
                    case 0x04:
//                        Speed_Handle(0x05);
//                        if ((mcQEP.ZeroCntrOld  < mcQEP.ZeroCntr) && (mcQEP.ZeroNewCntr > 0x1FFF))
//                        {
//                            mcSP.PulsesNum = mcQEP.ZeroCntrOld + mcQEP.ZeroNewCntr;
//                        }
//                        else 
//                        {
                            mcSP.PulsesNum = mcQEP.ZeroCntr + mcQEP.ZeroNewCntr;
//                        }
                        break;
                        
                    case 0x08://写零位81 01 06 08 FF
											   //mcQEP.CntrSum_ZeroTemp = mcQEP.CntrSumReal;
//                        Speed_Handle(0x05);
                        mcQEP.ZeroNewCntr = mcQEP.CntrSumReal - mcQEP.ZeroCntr;
                        Flash_Data[0] = mcQEP.AngleFlt >> 8;
                        Flash_Data[1] = mcQEP.AngleFlt;
                        Flash_Data[2] = mcQEP.ZeroNewCntr >> 24;
                        Flash_Data[3] = mcQEP.ZeroNewCntr >> 16;
                        Flash_Data[4] = mcQEP.ZeroNewCntr >> 8;
                        Flash_Data[5] = mcQEP.ZeroNewCntr;
                        EA = 0;
                        Flash_ErasePageRom(STARTPAGEROMADDRESS);
                        
                        Flash_Sector_Write(STARTPAGEROMADDRESS, Flash_Data[0]);
                        Flash_Sector_Write(STARTPAGEROMADDRESS+1, Flash_Data[1]);
                        Flash_Sector_Write(STARTPAGEROMADDRESS+2, Flash_Data[2]);
                        Flash_Sector_Write(STARTPAGEROMADDRESS+3, Flash_Data[3]);
                        Flash_Sector_Write(STARTPAGEROMADDRESS+4, Flash_Data[4]);
                        Flash_Sector_Write(STARTPAGEROMADDRESS+5, Flash_Data[5]);
                        EA = 1;
                        
                        break;
												
                    case 0x22://电机停止命令。81 01 06 22 FF
												if (Uart.UsaRxLen == 6)
												{
													isCtrlPowerOn = false;
													Uart.T_Len = 3;
													Uart.RxFSM = 1;
												}
										case 0x33://电机启动命令。81 01 06 33 FF
												if (Uart.UsaRxLen == 6)
												{
													isCtrlPowerOn = true;
													Uart.T_Len = 3;
													Uart.RxFSM = 1;
												}
                        break;
                        
                    default:
                        break;
                }
                
                break;
                //            default:
                //                break;
            
            case 0x02:
                switch (Uart.R_DATA[2])
                {
                    case 0x38:                        
                        
                        Uart.T_DATA[0] = 0x90;
                        Uart.T_DATA[1] = 0x50;
                        Uart.T_DATA[2] = 0x01;
                        Uart.T_DATA[3] = 0x00;
                  
                        Uart.T_Len = 5;
                        Uart.RxFSM = 1;
                        
                        break;
                    
                    case 0x48:
                            
                        Uart.T_DATA[0] = 0x90;
                        Uart.T_DATA[1] = 0x50;
                        Uart.T_DATA[2] = 0x01;
                        Uart.T_DATA[3] = 0x00;
                  
                        Uart.T_Len = 5;
                        Uart.RxFSM = 1;
                        
                        break;
                    
                    case 0x68:
                        
                        Uart.T_DATA[0] = 0x90;
                        Uart.T_DATA[1] = 0x50;
                        Uart.T_DATA[2] = (SKP >> 4) & 0x0F;
                        Uart.T_DATA[3] = SKP;
                        
                        Uart.T_Len = 5;
                        Uart.RxFSM = 1;
                    
                        break;
                   case 0x69:
                        
                        Uart.T_DATA[0] = 0x90;
                        Uart.T_DATA[1] = 0x50;
                        Uart.T_DATA[2] = (SKI >> 4) & 0x0F;
                        Uart.T_DATA[3] = SKI;
                        
                        Uart.T_Len = 5;
                        Uart.RxFSM = 1;
                    
                        break;
                   
                    case 0x6A:
                        
                        Uart.T_DATA[0] = 0x90;
                        Uart.T_DATA[1] = 0x50;
                        Uart.T_DATA[2] = (SKD >> 4) & 0x0F;
                        Uart.T_DATA[3] = SKD;
                    
                        Uart.T_Len = 5;
                        Uart.RxFSM = 1;
                    
                        break;
                    
                   case 0x78:
                        
                        Uart.T_DATA[0] = 0x90;
                        Uart.T_DATA[1] = 0x50;
                        if (mcState != mcFault)
                        {
                            Uart.T_DATA[2] = 0x05;                          
                        }
                        else 
                        {
                            Uart.T_DATA[2] = 0x04;
                        } 
                        
                        Uart.T_Len = 4;
                        Uart.RxFSM = 1;
                    
                        break;
                        
                  case 0x88:
                        									
//												mcFaultSource = FaultNoSource;
												mcFaultDect.CurrentFlag = 0;

												Uart.T_DATA[0] = 0x90;
												Uart.T_DATA[1] = 0x50;
                        if (mcState != mcFault)
                        {
													  
                            Uart.T_DATA[2] = 0x06; 
														
                        }
                        else 
                        {
                            Uart.T_DATA[2] = 0x04;
                        } 
                        Uart.T_Len = 4;
												Uart.RxFSM = 1;

                    
                        break;
                }
                break;
                
            case 0x09:
                switch (Uart.R_DATA[2])
                {
                    case 0x04:
                        Uart.T_DATA[0] = 0x90;
                        Uart.T_DATA[1] = 0x50;
                        if (Learn.FilishFlag)
                        {
                            Uart.T_DATA[2] = 0x02;                          
                        }
                        else 
                        {
                            Uart.T_DATA[2] = 0x03;
                        }
                        
                        Uart.T_Len = 4;
                        Uart.RxFSM = 1;
                        break;
                    
                    case 0x06:                      
                        switch (Uart.R_DATA[3])
                        {
                            case 0x11:
                                    mcSP.Speedlevel = (float)(ABS(mcQEP.SpeedMFlt) * MOTOR_SPEED_BASE / 32767.0 - 0.333)/0.833;

                                    
                                    Uart.T_DATA[0] = 0x90;
                                    Uart.T_DATA[1] = 0x50;
                                    Uart.T_DATA[2] = 0x11;
                                    Uart.T_DATA[3] = mcSP.Speedlevel;
                              
                                    Uart.T_Len = 5;
                                    Uart.RxFSM = 1;
                                
                                break;
                            
                            case 0x12:
                                    PosiAngle = mcQEP.CntrSumReal - mcQEP.ZeroCntr - mcQEP.ZeroNewCntr;
                                   // PosiAngle = PosiAngle << 2;
                                    Uart.T_DATA[0] = 0x90;
                                    Uart.T_DATA[1] = 0x50;
                                    Uart.T_DATA[2] = (PosiAngle >> 12) & 0x0F;
                                    Uart.T_DATA[3] = (PosiAngle >> 8) & 0x0F;
                                    Uart.T_DATA[4] = (PosiAngle >> 4) & 0x0F;
                                    Uart.T_DATA[5] = PosiAngle & 0x0F;
                              
                                    Uart.T_Len = 7;
                                    Uart.RxFSM = 1;
                                
                                break;
                        }
                        break;
                }
                break;
        }
        if (Uart.RxFSM == 1)
        {
            UartDealResponse();
            Uart.RxFSM = 0;
        }
        Uart.ResponceFlag = 0;
    }
		
		
}




void Fault_Communication(void)
{
    if (Uart.Read_State)
    {
        if (Uart.Time_Count < 200) //100 ms
        {
            Uart.Time_Count++;
        }
        else
        {
            Uart.UARxCnt = 0;
            Uart.Read_State = 0;
            Uart.ResponceFlag = 0;
        }
    }
    else
    {
        Uart.Time_Count = 0;
    }
}





void Self_Learning(void)
{
	if (Learn.State != LearnOver)
	{
		mcSP.PulsesNum = mcQEP.CntrSumReal + 3000;
//        mcSpeedRampLim.ActualValueFlt = 30000;
		isCtrlPowerOn = true;
		if (mcQEP.ZSaveFlag ==1)
		{
			//isCtrlPowerOn = false;
			Learn.State = LearnOver;
		}
	}
	else
	{
//        speedRef =  S_Value(0.0);
//        Speed_Handle(0x00);
		  mcSP.PulsesNum = mcQEP.ZeroCntr + mcQEP.ZeroNewCntr;
//          mcSP.PulsesNum = mcQEP.CntrSumReal;
          Learn.FilishFlag = 1;
//		isCtrlPowerOn = true;
//		mcSP.PulsesNum =8192;
	}
  
}
