"""Ejecuta y verifica secuencialmente el flujo de Software FJ."""

import logging
from decimal import Decimal, localcontext
from functools import partial
from pathlib import Path

from modelos import (
    Asesoria, DatosInvalidos, Equipo, ErrorCalculo, Estado,
    NoDisponible, OperacionNoPermitida, Sala,
)
from sistema import SistemaReservas


def verificar(condicion, mensaje):
    """Las verificaciones se ejecutan incluso si Python usa la opción -O."""
    if not condicion:
        raise AssertionError(mensaje)


def ejecutar_caso(numero, nombre, operacion, esperado, log):
    """Aísla cada operación y distingue los rechazos esperados de los fallos."""
    etiqueta = f"{numero:02d}. {nombre}"
    try:
        resultado = operacion()
    except Exception as error:
        # El archivo conserva la traza y cualquier excepción encadenada.
        log.exception("%s | %s", etiqueta, type(error).__name__)
        if esperado is not None and isinstance(error, esperado):
            print(f"[OK] {etiqueta} | Rechazo esperado: {error}")
            return True
        print(f"[FALLO] {etiqueta} | {type(error).__name__}: {error}")
        return False
    else:
        if esperado is not None:
            log.error("%s | Faltó el rechazo %s", etiqueta, esperado.__name__)
            print(f"[FALLO] {etiqueta} | Faltó el rechazo {esperado.__name__}.")
            return False
        detalle = resultado.describir() if hasattr(resultado, "describir") else resultado
        log.info("%s | %s", etiqueta, detalle)
        print(f"[OK] {etiqueta} | {detalle}")
        return True
    finally:
        # Se registra el cierre tanto si una operación termina como si se rechaza.
        log.info("%s | Fin de operación", etiqueta)


def casos_de_simulacion(sistema):
    """Ordena las operaciones según las dependencias entre registros."""
    cliente = sistema.registrar_cliente
    servicio = sistema.registrar_servicio
    reservar = sistema.crear_reserva
    confirmar = sistema.confirmar_reserva
    cancelar = sistema.cancelar_reserva
    examinar = sistema.consultar_reserva

    def confirmar_sin_precision():
        # Acota el cambio de precisión a esta prueba y fuerza un error de redondeo.
        with localcontext() as contexto:
            contexto.prec = 2
            confirmar("R-01")

    def verificar_pendiente():
        reserva = examinar("R-01")
        verificar(reserva.estado is Estado.PENDIENTE, "Cambió el estado tras el error.")
        verificar(reserva.total is None, "Se guardó un total antes de confirmar.")
        return reserva

    def verificar_totales():
        # Importes calculados a mano para contrastar las tres fórmulas.
        for codigo, importe in (
            ("R-01", "214200.00"), ("R-02", "50000.00"),
            ("R-04", "75000.00"), ("R-05", "100000.00"),
        ):
            verificar(examinar(codigo).total == Decimal(importe), f"Importe de {codigo}.")
        verificar(examinar("R-01").estado is Estado.CANCELADA, "R-01 sigue activa.")
        verificar(examinar("R-03").estado is Estado.PENDIENTE, "R-03 cambió de estado.")
        return "Cuatro importes y dos estados coherentes"

    # Cada fila define el nombre, la operación y su excepción esperada, si aplica.
    return [
        ("Alta de cliente válido", partial(cliente, "C-01", "Lina Pérez", "lina@example.com"), None),
        ("Correo inválido", partial(cliente, "C-02", "Ana Ruiz", "ana-sin-arroba"), DatosInvalidos),
        ("Nombre obligatorio vacío", partial(cliente, "C-02", " ", "ana@example.com"), DatosInvalidos),
        ("Alta válida tras los rechazos", partial(cliente, "C-02", "Ana Ruiz", "ana@example.com"), None),
        ("Cliente duplicado", partial(cliente, "c-01", "Lina Pérez", "lina@example.com"), OperacionNoPermitida),
        ("Registro de sala", partial(servicio, Sala, "S-01", "Sala Andina", 100000, 20), None),
        ("Tarifa de equipo inválida", partial(servicio, Equipo, "S-02", "Proyector", "abc", 4), DatosInvalidos),
        ("Registro de equipo", partial(servicio, Equipo, "S-02", "Proyector", 12500, 4), None),
        ("Registro de asesoría", partial(servicio, Asesoria, "S-03", "Arquitectura", 60000), None),
        ("Registro de asesoría deshabilitada", partial(servicio, Asesoria, "S-04", "Soporte", 45000, False), None),
        ("Reserva para cliente inexistente", partial(reservar, "R-01", "C-99", "S-01", 2), OperacionNoPermitida),
        ("Reserva con exceso de asistentes", partial(reservar, "R-01", "C-01", "S-01", 2, cantidad=21), DatosInvalidos),
        ("Creación de reserva de sala", partial(reservar, "R-01", "C-01", "S-01", 2, cantidad=10), None),
        ("Confirmación con impuesto inválido", partial(confirmar, "R-01", impuesto=101), DatosInvalidos),
        ("Fallo aritmético controlado", confirmar_sin_precision, ErrorCalculo),
        ("Verificación del estado tras el fallo", verificar_pendiente, None),
        ("Confirmación con impuesto y descuento", partial(confirmar, "R-01", impuesto=19, descuento=10), None),
        ("Creación de reserva de equipo", partial(reservar, "R-02", "C-02", "S-02", 2, cantidad=2), None),
        ("Confirmación de equipo por dos unidades", partial(confirmar, "R-02"), None),
        ("Creación de reserva de servicio deshabilitado", partial(reservar, "R-03", "C-02", "S-04", 1), None),
        ("Rechazo de servicio deshabilitado", partial(confirmar, "R-03"), NoDisponible),
        ("Creación de reserva de asesoría", partial(reservar, "R-04", "C-01", "S-03", 1), None),
        ("Confirmación de asesoría", partial(confirmar, "R-04"), None),
        ("Segunda solicitud para la sala", partial(reservar, "R-05", "C-02", "S-01", 1), None),
        ("Rechazo por ocupación de sala", partial(confirmar, "R-05"), NoDisponible),
        ("Cancelación y liberación de la sala", partial(cancelar, "R-01"), None),
        ("Rechazo de cancelación repetida", partial(cancelar, "R-01"), OperacionNoPermitida),
        ("Reintento exitoso tras liberar la sala", partial(confirmar, "R-05"), None),
        ("Comprobación de estados e importes", verificar_totales, None),
    ]


def main():
    """Abre la bitácora, ejecuta todos los casos y cierra el archivo."""
    ruta = Path(__file__).resolve().with_name("software_fj.log")
    log = logging.getLogger("software_fj")
    log.setLevel(logging.INFO)
    log.propagate = False
    try:
        archivo = logging.FileHandler(ruta, encoding="utf-8")
    except OSError as error:
        print(f"No se pudo abrir la bitácora {ruta.name}: {error}")
        return 1

    archivo.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
    log.addHandler(archivo)
    try:
        casos = casos_de_simulacion(SistemaReservas())
        print("Software FJ | Simulación secuencial")
        log.info("Inicio de la simulación")
        aprobados = sum(
            ejecutar_caso(numero, nombre, operacion, esperado, log)
            for numero, (nombre, operacion, esperado) in enumerate(casos, 1)
        )
        resumen = f"{aprobados}/{len(casos)} comprobaciones aprobadas."
        print(resumen)
        log.info(resumen)
        return 0 if aprobados == len(casos) else 1
    finally:
        log.removeHandler(archivo)
        archivo.close()


if __name__ == "__main__":
    raise SystemExit(main())
