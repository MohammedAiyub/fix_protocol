import datetime
import quickfix as fix
import quickfix50sp2 as fix50sp2

class FixClient(fix.Application):
    def __init__(self):
        super().__init__()
        self.callbacks = None

    def initialize(self, callbacks={}):
        self.callbacks = callbacks

    def onCreate(self, sessionID):
        return

    def onLogon(self, sessionID):
        self.sessionID = sessionID
        callbacks = self.callbacks.get('on_connect')
        if callbacks:
            callbacks(sessionID)
        return

    def onLogout(self, sessionID):
        callbacks = self.callbacks.get('on_disconnect')
        if callbacks:
            callbacks(sessionID)
        return

    def toAdmin(self, sessionID, message):
        return

    def fromAdmin(self, message, sessionID):
        return

    def toApp(self, sessionID, message):
        return

    def fromApp(self, message, sessionID):
        callbacks = self.callbacks.get('on_data')
        if callbacks:
            callbacks(message, sessionID)
        return

    def generate_client_id(self):
        self.execID = self.execID + 1
        return str(self.execID)

    def place_order(self, account: str, exchange: str, symbol: str, side: str, qty: float, price: float, client_id: str,
                    amount: float, ord_type: str, stop_fx: float):
        side = fix.Side_BUY if side == "buy" else fix.Side_SELL

        trade = fix.Message()
        trade.getHeader().setField(fix.BeginString(fix.BeginString_FIXT11))  #
        trade.getHeader().setField(fix.MsgType(fix.MsgType_NewOrderSingle))  # 35=D
        trade.setField(fix.ClOrdID(client_id))  # 11=Unique order
        trade.setField(fix.Symbol(symbol))  # 55=SMBL ?
        trade.setField(fix.Side(side))  # 43=1 Buy
        if ord_type in ["limit", "stop limit"]:
            trade.setField(fix.OrderQty(qty))
            if ord_type == "limit":
                trade.setField(fix.OrdType(fix.OrdType_LIMIT))  # 40=2 Limit order
            else:
                trade.setField(fix.OrdType(fix.OrdType_STOP_LIMIT))  # 40=2  stop Limit
                trade.setField(fix.StopPx(stop_fx))  # 99
            trade.setField(fix.Price(price))  # 44=10
            trade.setField(fix.TimeInForce(fix.TimeInForce_GOOD_TILL_CANCEL))
        else:
            trade.setField(fix.OrdType(fix.OrdType_MARKET))  # 40=1 Order type
            if side == "buy":
                trade.setField(fix.CashOrderQty(amount))
            else:
                trade.setField(fix.OrderQty(qty))

        t = fix.TransactTime()
        t.setString(datetime.datetime.utcnow().strftime("%Y%m%d-%H:%M:%S.%f")[:-3])
        trade.setField(t)
        fix.Session.sendToTarget(trade, self.sessionID)

    def place_cancel(self, account: str, exchange: str, symbol: str, uni_cli_id: str, original_id: str, side: str):
        side = fix.Side_BUY if side == "buy" else fix.Side_SELL
        trade = fix.Message()
        trade.getHeader().setField(fix.BeginString(fix.BeginString_FIX44))
        trade.getHeader().setField(fix.MsgType(fix.MsgType_OrderCancelRequest))
        trade.setField(fix.Account(account))
        trade.setField(fix.ClOrdID(uni_cli_id))  # 11=Unique order
        trade.setField(fix.OrderID('0'))
        trade.setField(fix.OrigClOrdID(original_id))
        trade.setField(fix.Side(side))  # 43=1 Buy
        trade.setField(fix.Symbol(symbol))  # 55=SMBL ?
        t = fix.TransactTime()
        t.setString(datetime.datetime.utcnow().strftime("%Y%m%d-%H:%M:%S.%f")[:-3])
        trade.setField(t)
        trade.setField(fix.SecurityExchange(exchange))
        fix.Session.sendToTarget(trade, self.sessionID)


def main():
    def on_connect(sesion_id):
        pass

    def on_disconnect(session_id):
        print(f"{session_id} disconnected")

    def on_data(message, session_id):
        print(f"Data: {message}")

    try:
        file_name = 'gemini_og_client.yml'
        application = FixClient()
        application.initialize({"on_connect": on_connect,
                                "on_disconnect": on_disconnect,
                                "on_data": on_data})
        settings = fix.SessionSettings(file_name)
        storeFactory = fix.FileStoreFactory(settings)
        logFactory = fix.ScreenLogFactory(settings)
        #logFactory = fix.FileLogFactory(settings)
        initiator = fix.SocketInitiator(application, storeFactory, settings, logFactory)
        initiator.start()
        # time.sleep(0.001)
        exchange = "gemini"
        while 1:
            print("1: market order\n2: limit order\n3: stop limit\n4: cancel order \n")
            option = int(input())
            price = 0
            if option in [1, 2, 3]:
                symbol = input("Symbol<BTCUSD>: ").upper()
                side = input("Side<buy>: ").lower()
                qty = float(input("Qty<0.001>: "))
                price = float(input("Price<92.8>: ")) if option in [2,3] else 0
                c_id = input("Client ID<test1>: ")
                order_type = "market" if option == 1 else "limit" if option == 2 else "stop limit"
                amount = float(input("Amount: ")) if order_type == "market" and side == "buy" else 0
                if order_type == "stop limit":
                    if side == "buy":
                        stopfx = float(input("stopfx(<=price): "))
                        while stopfx > price:
                            print("stopfx must be < or = to price")
                            stopfx = float(input("stopfx(<=price): "))
                    else:
                        stopfx = float(input("stopfx(>=price): "))
                        while stopfx < price:
                            print("stopfx must be > or = to price")
                            stopfx = float(input("stopfx(<=price): "))
                else:
                    stopfx = 0
                application.place_order(
                    account=f"1.{exchange}", exchange=exchange, symbol=symbol, side=side, qty=qty, price=price,
                    client_id=c_id, amount=amount, ord_type=order_type, stop_fx=stopfx )
            elif option == 4:
                symbol = input("Symbol<BTCUSD>: ").upper()
                side = input("Side<buy>: ").lower()
                ord_id = input("cli_order_id<test54>: ")
                uni_id = input("unique_id: ")
                application.place_cancel(
                    account=f"1.{exchange}", exchange=exchange, symbol=symbol, uni_cli_id=uni_id, original_id=ord_id, side=side)
    except (fix.ConfigError, fix.RuntimeError) as e:
        print(e)


if __name__ == '__main__':
    main()

