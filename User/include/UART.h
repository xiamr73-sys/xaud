#ifndef __UART_H__
#define __UART_H__


typedef struct
{
    uint8    R_DATA[20];//={0,0,0,0,0,0,0,0,0,0,0,0};      //接受数据数组
    uint8    T_DATA[20];//={0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0};      //发送数据数组
    uint16   Uredata;            //用于读取数据寄存器数据
    uint16   UARxCnt;            //接收数组索引
    uint16   RxFSM;              //接收数据处理完成标准
    uint16   UsaRxLen;
    uint16   flagUsaRxComm;
    uint32   CheckDate;
    uint16   ResponceCount;
    uint8    ResponceFlag;       //数据读取完成标标志
    uint16	 UsaTxlen;
    uint16   SendCnt;            //发送数组索引
	uint8    T_Len;              //发送数据长度
	uint8    R_Len;							 //接收数据长度
	uint16   Time_Count;		   	 //运行时间计时
//	uint8    Send_Overflag;      //发送数据完成标志
	uint8    Send_Set;           //发送数据选择
    uint8    Read_State;
    uint8    Go_State;
  
    uint32   Go_Time;
    uint32   Go_Time2;

    uint8    EnableTimeCnt;
    
    uint8    EnableTimeCnt2;

    uint8    Speed_Level;  
    uint8    SendSpeed_Flag;
}MCUART;

typedef enum
{
  PowerOn    = 0,
  TurnLeft   = 1,
  TurnRight  = 2,
  TurnMiddle = 3,
  Fix        = 4,//固定住
  InitOver   = 5,//初始化结束
  
  LearnOver  = 6,//学习结束

}StaType;

typedef struct
{   
    StaType    State;
    uint8    LastState;
    uint8    FirstTime;
    uint8    PowerFlag;
    uint8    StartFlag;
    uint8    FilishFlag;
  
    uint8    Reign ;

    uint8    Run_Time;
    uint8    CheckTime;
    uint8    Result;
    uint8    HideTime; 
    int32    AngleBias;                 //0°时候的脉冲数
    int32    AngleBase;                 //229.5°时候的脉冲数
}SELFLEARN;


typedef struct
{   
	uint8 flag_0;
	uint8 flag_90;
	uint8 flag_180;
	uint8 flag_270;
	
}UART_FLAG;

extern SELFLEARN Learn;
extern SELFLEARN Power;
extern UART_FLAG xdata UARTFL;

extern MCUART Uart;
extern uint16 MinAngleCode  ; //306 
extern uint16 MaxAngleCode  ; //14CD         
extern uint16 MiddleAngleCode  ;
extern void UART_Init(void);
extern void UART_SendData(uint8 T_Data);
extern void UartDealResponse(void);
extern void UartDealComm(void);
extern void UartDealComm2(void);

extern void StopCurve(void);

extern void Uart1sSent(void);
extern void Fault_Communication(void);

/*************************************************************************************///External Function
extern void UART1_Init(void);
extern void UART2_Init(void);

extern void Self_Learning(void);
extern void PowerOnMove(void); //上电动作

extern void Send_ACK(void);
extern void Send_NoActive(void); //无效指令
extern void Send_Success(void);
extern void Send_Fail(void);
extern void Speed_Handle(uint8 level);

#endif