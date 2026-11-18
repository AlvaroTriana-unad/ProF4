"""Registra y consulta entidades en listas internas sin persistir datos."""

from modelos import Cliente, DatosInvalidos, Entidad, OperacionNoPermitida, Reserva, Servicio


class SistemaReservas:
    def __init__(self):
        self.__clientes = []
        self.__servicios = []
        self.__reservas = []

    @staticmethod
    def __buscar(lista, codigo):
        # Se reutiliza la misma regla de normalización al buscar y al registrar.
        codigo = codigo.strip().upper() if isinstance(codigo, str) else codigo
        for objeto in lista:
            if objeto.codigo == codigo:
                return objeto
        raise OperacionNoPermitida("No existe un registro con ese código.")

    @staticmethod
    def __guardar(lista, objeto: Entidad):
        if any(registro.codigo == objeto.codigo for registro in lista):
            raise OperacionNoPermitida(f"El código {objeto.codigo} ya está registrado.")
        lista.append(objeto)
        return objeto

    def registrar_cliente(self, codigo, nombre, correo):
        return self.__guardar(self.__clientes, Cliente(codigo, nombre, correo))

    def registrar_servicio(self, clase, *args, **datos):
        # El catálogo solo admite implementaciones del contrato Servicio.
        if not isinstance(clase, type) or not issubclass(clase, Servicio):
            raise DatosInvalidos("Se requiere un tipo de servicio válido.")
        return self.__guardar(self.__servicios, clase(*args, **datos))

    def crear_reserva(self, codigo, codigo_cliente, codigo_servicio, duracion, *, cantidad=1):
        cliente = self.__buscar(self.__clientes, codigo_cliente)
        servicio = self.__buscar(self.__servicios, codigo_servicio)
        reserva = Reserva(codigo, cliente, servicio, duracion, cantidad=cantidad)
        return self.__guardar(self.__reservas, reserva)

    def confirmar_reserva(self, codigo, *, impuesto=0, descuento=0):
        reserva = self.__buscar(self.__reservas, codigo)
        reserva.confirmar(impuesto=impuesto, descuento=descuento)
        return reserva

    def cancelar_reserva(self, codigo):
        reserva = self.__buscar(self.__reservas, codigo)
        reserva.cancelar()
        return reserva

    def consultar_reserva(self, codigo):
        return self.__buscar(self.__reservas, codigo)
