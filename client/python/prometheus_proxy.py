import atexit
import logging
import threading

import pika
import prometheus_client


# TODO: Add prometheus counters in this file.
CLOSE_EVENT_TIMEOUT_SECONDS = 5
DEFAULT_HEARTBEAT_INTERVAL_SECS = 5
PROCESS_DATA_EVEMTS_LIMIT = 0.1


class _PrometheusMetricsServer(threading.Thread):

    def __init__(self, connection_params, exchange, routing_key, exclusive, 
                 use_heartbeat_thread=True, heartbeat_interval=DEFAULT_HEARTBEAT_INTERVAL_SECS):
        super().__init__()
        self._connection_params = connection_params
        self._exchange = exchange
        self._routing_key = routing_key
        self._exclusive = exclusive
        self._connection = None
        self._channel = None
        self._close_event = threading.Event()
        # Connecting in ctor, so that an exception will be raised in case of bad parameters.
        self._connect()
        self._running = True
        self._heartbeat_interval = heartbeat_interval
        self._use_heartbeat_thread = use_heartbeat_thread

    def stop(self):
        try:
            self._running = False
            if self._connection.is_open:
                self._connection.close()
        finally:
            self._close_event.set()

    def run(self):
        if self._use_heartbeat_thread:
            self._start_heartbeat_thread()
        while self._running:
            try:
                if not self._connection.is_open:
                    self._connect()
                self._amqp_loop()
            except:
                logging.exception("Exception in AMQP loop")
                if self._connection.is_open and self._running:
                    self._connection.close()
        self.stop()

    def _connect(self):
        self._connection = pika.BlockingConnection(self._connection_params)
        self._channel = self._connection.channel()
        self._channel.exchange_declare(self._exchange, durable=True)
        self._channel.queue_declare(self._routing_key, auto_delete=True)
        self._channel.queue_bind(self._routing_key, self._exchange)

    def _amqp_loop(self):
        for method, props, unused_body in self._channel.consume(
                self._routing_key, exclusive=self._exclusive, auto_ack=True):
            self._channel.basic_publish(
                "",
                props.reply_to,
                prometheus_client.generate_latest(prometheus_client.REGISTRY),
                pika.BasicProperties(correlation_id=props.correlation_id),
            )

    def _start_heartbeat_thread(self):
        self._heartbeat_thread = threading.Thread(
            target=self._heartbeat_loop,
            daemon=True,
            name="prometheus_proxy.heartbeat",
        )
        self._heartbeat_thread.start()

    def _heartbeat_loop(self):
        while self._running:
            if self._connection.is_open:
                try:
                    self._connection.process_data_events(PROCESS_DATA_EVEMTS_LIMIT)
                except:
                    logging.exception("failed processing data events")
            self._close_event.wait(timeout=self._heartbeat_interval)



def start_amqp_server(connection_params, exchange, routing_key, exclusive=True):
    """Starts an AMQP server for prometheus metrics as a daemon thread."""
    t = _PrometheusMetricsServer(connection_params, exchange, routing_key, exclusive)
    t.daemon = True
    def stop():
        t._running = False
        t._connection.add_callback_threadsafe(t.stop)
        if not t._close_event.wait(CLOSE_EVENT_TIMEOUT_SECONDS):
            logging.error("Stop did not complete after %ss! "
                          "Exiting anyway, the rabbit server may still see the queue name as in use", CLOSE_EVENT_TIMEOUT_SECONDS)
    atexit.register(stop)
    t.start()

