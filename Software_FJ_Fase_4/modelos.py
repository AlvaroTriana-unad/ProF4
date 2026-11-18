"""Entidades y reglas de negocio de Software FJ."""

import re
from abc import ABC, abstractmethod
from decimal import Decimal, DecimalException, InvalidOperation, ROUND_HALF_UP
from enum import Enum


class ErrorSistema(Exception):
    """Error controlado que puede presentarse durante una operación."""


class DatosInvalidos(ErrorSistema):
    """Un dato obligatorio falta o está fuera del rango permitido."""


class NoDisponible(ErrorSistema):
    """El servicio no puede atender otra reserva en esta simulación."""


class OperacionNoPermitida(ErrorSistema):
    """La operación contradice el estado actual del sistema."""


class ErrorCalculo(ErrorSistema):
    """No se pudo producir un importe monetario válido."""


def texto(valor, campo, maximo):
    """Rechaza valores vacíos, caracteres de control y textos muy largos."""
    if not isinstance(valor, str) or not valor.strip():
        raise DatosInvalidos(f"{campo} es obligatorio.")
    valor = valor.strip()
    if len(valor) > maximo or not valor.isprintable():
        raise DatosInvalidos(f"{campo} tiene un formato inválido.")
    return valor


def entero(valor, campo, maximo):
    """Valida duraciones y cantidades; bool no representa una cantidad."""
    if type(valor) is not int or not 1 <= valor <= maximo:
        raise DatosInvalidos(f"{campo} debe ser un entero entre 1 y {maximo}.")
    return valor


def decimal_en_rango(valor, campo, minimo, maximo):
    """Convierte entradas a Decimal y conserva la causa si falla la conversión."""
    try:
        numero = Decimal(str(valor))
    except InvalidOperation as error:
        raise DatosInvalidos(f"{campo} debe ser un número válido.") from error
    if not numero.is_finite() or not minimo <= numero <= maximo:
        raise DatosInvalidos(f"{campo} debe estar entre {minimo} y {maximo}.")
    return numero


class Entidad(ABC):
    """Contrato común para objetos con un identificador de solo lectura."""

    def __init__(self, codigo):
        # Los códigos se normalizan para detectar duplicados sin distinguir mayúsculas.
        self.__codigo = texto(codigo, "Código", 24).upper()
        if not re.fullmatch(r"[A-Z0-9-]+", self.__codigo):
            raise DatosInvalidos("El código solo admite letras, números y guiones.")

    @property
    def codigo(self):
        return self.__codigo

    @abstractmethod
    def describir(self):
        """Devuelve una descripción segura para la demostración."""


class Cliente(Entidad):
    """Mantiene los datos personales en atributos privados."""

    def __init__(self, codigo, nombre, correo):
        super().__init__(codigo)
        self.__nombre = texto(nombre, "Nombre", 100)
        if not any(letra.isalpha() for letra in self.__nombre):
            raise DatosInvalidos("El nombre debe contener letras.")
        correo = texto(correo, "Correo", 254)
        if not re.fullmatch(r"[^@\s]+@[^@\s.]+(?:\.[^@\s.]+)+", correo):
            raise DatosInvalidos("El formato del correo es inválido.")
        self.__correo = correo

    def describir(self):
        # La descripción excluye nombre y correo para protegerlos en el registro.
        return f"Cliente {self.codigo} registrado"


class Servicio(Entidad):
    """Centraliza la tarifa, la disponibilidad y el cálculo en pesos colombianos."""

    def __init__(self, codigo, nombre, tarifa, disponible=True):
        super().__init__(codigo)
        self._nombre = texto(nombre, "Nombre del servicio", 80)
        self._tarifa = decimal_en_rango(tarifa, "Tarifa", Decimal("0.01"), 10**9)
        if type(disponible) is not bool:
            raise DatosInvalidos("Disponible debe ser verdadero o falso.")
        self.__habilitado = disponible
        self.__reserva_activa = None

    @property
    def disponible(self):
        # Sin agenda en el enunciado, cada servicio admite una confirmación activa.
        return self.__habilitado and self.__reserva_activa is None

    def ocupar(self, reserva):
        if not self.disponible:
            raise NoDisponible(f"El servicio {self.codigo} no está disponible.")
        self.__reserva_activa = reserva

    def liberar(self, reserva):
        if self.__reserva_activa is not reserva:
            raise OperacionNoPermitida("La reserva no ocupa este servicio.")
        self.__reserva_activa = None

    @abstractmethod
    def validar_parametros(self, duracion, cantidad):
        """Comprueba las reglas particulares de cada servicio."""

    @abstractmethod
    def calcular_costo(self, duracion, *, cantidad=1, impuesto=0, descuento=0):
        """Admite costo base y variantes por opciones de llamada."""

    def _total(self, base, impuesto, descuento):
        # Los porcentajes se expresan de 0 a 100.
        impuesto = decimal_en_rango(impuesto, "Impuesto", 0, 100)
        descuento = decimal_en_rango(descuento, "Descuento", 0, 100)
        try:
            neto = base * (1 - descuento / 100)
            total = (neto * (1 + impuesto / 100)).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
        except DecimalException as error:
            raise ErrorCalculo("No se pudo redondear el total.") from error
        else:
            if not total.is_finite() or total < 0:
                raise ErrorCalculo("El total es inconsistente.")
            return total


class Sala(Servicio):
    """Alquiler por hora con límite de asistentes."""

    def __init__(self, codigo, nombre, tarifa, capacidad, disponible=True):
        super().__init__(codigo, nombre, tarifa, disponible)
        self.__capacidad = entero(capacidad, "Capacidad", 200)

    def describir(self):
        return f"Sala {self.codigo} ({self._nombre}), hasta {self.__capacidad} asistentes"

    def validar_parametros(self, duracion, cantidad):
        entero(duracion, "Horas de sala", 12)
        entero(cantidad, "Asistentes", self.__capacidad)

    def calcular_costo(self, duracion, *, cantidad=1, impuesto=0, descuento=0):
        self.validar_parametros(duracion, cantidad)
        return self._total(self._tarifa * duracion, impuesto, descuento)


class Equipo(Servicio):
    """Alquiler por hora y por unidad, limitado a las unidades disponibles."""

    def __init__(self, codigo, nombre, tarifa, unidades, disponible=True):
        super().__init__(codigo, nombre, tarifa, disponible)
        self.__unidades = entero(unidades, "Unidades", 100)

    def describir(self):
        return f"Equipo {self.codigo} ({self._nombre}), hasta {self.__unidades} unidades"

    def validar_parametros(self, duracion, cantidad):
        entero(duracion, "Horas de alquiler", 72)
        entero(cantidad, "Unidades solicitadas", self.__unidades)

    def calcular_costo(self, duracion, *, cantidad=1, impuesto=0, descuento=0):
        self.validar_parametros(duracion, cantidad)
        return self._total(self._tarifa * duracion * cantidad, impuesto, descuento)


class Asesoria(Servicio):
    """Asesoría individual por hora, con un cargo fijo de preparación."""

    def describir(self):
        return f"Asesoría {self.codigo} ({self._nombre}), atención individual"

    def validar_parametros(self, duracion, cantidad):
        entero(duracion, "Horas de asesoría", 4)
        entero(cantidad, "Participantes", 1)

    def calcular_costo(self, duracion, *, cantidad=1, impuesto=0, descuento=0):
        self.validar_parametros(duracion, cantidad)
        return self._total(self._tarifa * duracion + Decimal("15000"), impuesto, descuento)


class Estado(Enum):
    PENDIENTE = "pendiente"
    CONFIRMADA = "confirmada"
    CANCELADA = "cancelada"


class Reserva(Entidad):
    """Controla las transiciones y conserva el importe una vez confirmado."""

    def __init__(self, codigo, cliente, servicio, duracion, *, cantidad=1):
        super().__init__(codigo)
        if not isinstance(cliente, Cliente) or not isinstance(servicio, Servicio):
            raise DatosInvalidos("Se requiere un cliente y un servicio válidos.")
        servicio.validar_parametros(duracion, cantidad)
        self.__cliente = cliente
        self.__servicio = servicio
        self.__duracion = duracion
        self.__cantidad = cantidad
        self.__estado = Estado.PENDIENTE
        self.__total = None

    @property
    def estado(self):
        return self.__estado

    @property
    def total(self):
        return self.__total

    def describir(self):
        total = "" if self.total is None else f" | COP {self.total:,.2f}"
        return (
            f"Reserva {self.codigo} | cliente {self.__cliente.codigo} | "
            f"servicio {self.__servicio.codigo} | {self.__duracion} h | "
            f"{self.estado.value}{total}"
        )

    def procesar(self, *, impuesto=0, descuento=0):
        """Cotiza de forma polimórfica y traduce fallos de aritmética."""
        try:
            return self.__servicio.calcular_costo(
                self.__duracion, cantidad=self.__cantidad,
                impuesto=impuesto, descuento=descuento,
            )
        except DecimalException as error:
            raise ErrorCalculo("No se pudo calcular el importe de la reserva.") from error

    def confirmar(self, *, impuesto=0, descuento=0):
        if self.estado is not Estado.PENDIENTE:
            raise OperacionNoPermitida("Solo se confirma una reserva pendiente.")
        # La cotización termina antes de modificar el estado o la disponibilidad.
        total = self.procesar(impuesto=impuesto, descuento=descuento)
        self.__servicio.ocupar(self)
        self.__total = total
        self.__estado = Estado.CONFIRMADA

    def cancelar(self):
        if self.estado is Estado.CANCELADA:
            raise OperacionNoPermitida("La reserva ya está cancelada.")
        if self.estado is Estado.CONFIRMADA:
            self.__servicio.liberar(self)
        self.__estado = Estado.CANCELADA
