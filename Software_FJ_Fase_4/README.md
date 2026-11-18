# Software FJ

Sistema de clientes, servicios y reservas para la Fase 4 de Programación (213023), UNAD. Desarrollo individual.

## Ejecución

Desde la carpeta del proyecto, ejecuta `python main.py` con Python 3.12 o una versión posterior. El programa usa la biblioteca estándar y corre los casos en orden. Cada ejecución añade entradas a `software_fj.log`. Se necesita permiso de escritura en la carpeta.

- `modelos.py` implementa las entidades, los servicios, las reglas de costos y las excepciones.
- `sistema.py` administra listas privadas de clientes, servicios y reservas.
- `main.py` verifica 29 operaciones con datos ficticios y registra los resultados.

## Reglas de la simulación

| Servicio | Tarifa | Límite |
| --- | --- | --- |
| Sala | Por hora | 12 horas y capacidad definida por sala |
| Equipo | Por hora y unidad solicitada | 72 horas y existencias definidas por equipo |
| Asesoría | Por hora más COP 15.000 de preparación | 4 horas y un participante |

Cada servicio admite una reserva confirmada a la vez. Las solicitudes nacen pendientes. Confirmar exige disponibilidad y un cálculo válido. Cancelar una confirmación libera el servicio. Los registros viven en memoria durante una ejecución. La bitácora conserva eventos y errores sin escribir nombres ni correos de clientes.

`calcular_costo(horas)`, `calcular_costo(horas, impuesto=19)` y `calcular_costo(horas, cantidad=2, impuesto=19, descuento=10)` ilustran las variantes con argumentos opcionales. El último ejemplo aplica a servicios que admiten más de una unidad o persona. Se aplica el descuento antes del impuesto y el total se redondea a dos decimales.

## Validación

La secuencia comprueba datos obligatorios, duplicados, correo inválido, conversión numérica, disponibilidad, ocupación, cancelación y reintento. También fuerza un fallo aritmético con precisión decimal reducida y comprueba que una reserva pendiente conserve su estado y pueda confirmarse después. Las operaciones exitosas se registran como INFO y las excepciones como ERROR con sus trazas.
