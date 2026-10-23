# Instalación del servidor en AWS

La instancia que ya está en marcha se llama `cfdesign`. Este manual sirve para crear otra igual y para volver a levantar el código cada vez que `main` cambia. El archivo de Word con el mismo contenido está en [Instalacion-servidor-AWS.docx](Instalacion-servidor-AWS.docx).

El arranque del servidor es `compose.servidor.yaml`. Ese archivo no levanta Mailpit: el correo de confirmación sale por Gmail. La aplicación queda en el puerto **18080**. Sigue en `config.settings.development` porque, con HTTP, la configuración de producción marcaría las cookies como `Secure` y el navegador no guardaría la sesión.

## 1. La instancia que está hoy

Datos tomados de la consola de EC2 el 21 de octubre de 2026.

| Dato | Valor |
| --- | --- |
| Nombre | cfdesign |
| ID | i-07c39f84b1c7b3787 |
| Región | EE. UU. Este (Ohio), `us-east-2` |
| Estado | En ejecución |
| Tipo | t3.micro |
| AMI | ami-03e224e4dbc21f89e |
| Nombre de la AMI | al2023-ami-2023.12.20261014.0-kernel-6.18-x86_64 |
| Plataforma | Linux/UNIX, Amazon Linux 2023, x86_64 |
| Arranque | uefi |
| IMDSv2 | Obligatorio |
| VPC | vpc-0877ce6fabe7f919f |
| Subred | subnet-0065e8a11b4f527d8 |
| IP pública | 18.118.112.206, asignada automáticamente |
| DNS público | ec2-18-118-112-206.us-east-2.compute.amazonaws.com |
| IP privada | 172.31.24.67 |
| IP elástica | ninguna |
| Par de claves | cfdesign |
| Grupo de seguridad | launch-wizard-1, sg-05d3ffa45265dcd67 |
| Monitoreo detallado | desactivado |
| Protección de terminación | desactivada |

La IP pública no es elástica. Si la instancia se detiene y se vuelve a encender, AWS puede dar otra. En ese caso hay que cambiar la IP en el `.env` del servidor y en el origen de la aplicación de escritorio.

El grupo `default` (sg-03438b97b419876e4) también tiene una regla del puerto 18080, pero no es el grupo de esta instancia. Las reglas que importan son las de `launch-wizard-1`.

| Puerto | Protocolo | Origen | Para qué |
| --- | --- | --- | --- |
| 22 | TCP | 0.0.0.0/0 | SSH |
| 18080 | TCP | 0.0.0.0/0 | La aplicación |
| 443 | TCP | 0.0.0.0/0 | Abierto en la consola. El compose no lo usa: el sitio es HTTP en el 18080 |
| 8025 | TCP | 0.0.0.0/0 | Abierto en la consola. `compose.servidor.yaml` no publica Mailpit |

En una instancia nueva bastan el 22 y el 18080.

`t3.micro` tiene unos 913 MiB de memoria. Mientras Docker construye las imágenes, la sesión SSH puede cortarse con `Broken pipe`. Se vuelve a entrar y se repite el comando que quedó a medias. Una `t3.small` deja más margen.

## 2. Crear la instancia

En la consola de AWS, región **Ohio (us-east-2)**:

1. EC2 → Instancias → Lanzar instancias.
2. Nombre: `cfdesign`.
3. AMI: Amazon Linux 2023, kernel 6.x, arquitectura 64 bits (x86). La de esta máquina es `ami-03e224e4dbc21f89e`. Una Amazon Linux 2023 posterior, de 64 bits, también sirve.
4. Tipo: `t3.micro`.
5. Par de claves: crear o elegir `cfdesign` y guardar el archivo `cfdesign.pem`.
6. Red: la VPC y la subred de la tabla, con IP pública automática.
7. Grupo de seguridad nuevo, o `launch-wizard-1` si ya existe. Entrada TCP 22 y TCP 18080 desde `0.0.0.0/0`.
8. Almacenamiento: el volumen por defecto del asistente.
9. Metadatos: IMDSv2 obligatorio.
10. Lanzar.

Desde el Mac, con el `.pem` en la carpeta desde la que se trabaja:

```bash
chmod 400 cfdesign.pem
ssh -i "cfdesign.pem" ec2-user@ec2-18-118-112-206.us-east-2.compute.amazonaws.com
```

Si la IP cambió, se usa la IP pública o el DNS que muestre la consola en ese momento. El usuario es `ec2-user`.

## 3. Git, Docker, Compose y Buildx

Amazon Linux 2023 no tiene `apt-get`. El gestor es `dnf`, y hace falta `sudo`.

```bash
sudo dnf update -y
sudo dnf install -y git docker
sudo systemctl enable --now docker
sudo usermod -aG docker ec2-user
exit
```

Hay que salir y volver a entrar por SSH para que el grupo `docker` aplique. Después:

```bash
sudo mkdir -p /usr/libexec/docker/cli-plugins
sudo curl -SL "https://github.com/docker/compose/releases/download/v2.40.3/docker-compose-linux-x86_64" -o /usr/libexec/docker/cli-plugins/docker-compose
sudo chmod +x /usr/libexec/docker/cli-plugins/docker-compose
docker compose version

mkdir -p ~/.docker/cli-plugins
curl -SL "https://github.com/docker/buildx/releases/download/v0.38.0/buildx-v0.38.0.linux-amd64" -o ~/.docker/cli-plugins/docker-buildx
chmod +x ~/.docker/cli-plugins/docker-buildx
docker buildx version
```

`docker compose version` tiene que responder, y `docker buildx version` tiene que decir `v0.38.0` o posterior. Sin ese Buildx, `docker compose build` se niega a construir.

## 4. Clonar el repositorio

En la EC2 se crea una clave solo para leer GitHub. La clave privada se queda en el servidor. A GitHub se le pega únicamente la pública.

```bash
ssh-keygen -t rsa -b 4096 -C "correo-del-responsable"
cat ~/.ssh/id_rsa.pub
```

En GitHub, en `roque-code/FCDesign_client_server`, esa pública se agrega como deploy key de lectura, o como clave SSH de la cuenta. Si `ssh-keygen` pidió una frase de paso, `git pull` la va a pedir cada vez.

```bash
mkdir -p ~/fcdesign
cd ~/fcdesign
git clone git@github.com:roque-code/FCDesign_client_server.git
cd FCDesign_client_server
```

## 5. El archivo .env

`compose.servidor.yaml` ya trae el servidor de correo `smtp.gmail.com`, el puerto 587, TLS y la cuenta `aulivana.fcdesign@gmail.com`. La contraseña de aplicación de Gmail no va en el repositorio: el compose se niega a arrancar si falta en `.env`.

En `~/fcdesign/FCDesign_client_server/.env`:

```bash
DJANGO_SECRET_KEY=una-clave-larga-distinta-de-la-de-desarrollo
EMAIL_HOST_PASSWORD=clave-de-aplicacion-de-gmail
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,web,nginx,18.118.112.206
DJANGO_CSRF_ORIGINS=http://18.118.112.206:18080,http://127.0.0.1:18080,http://localhost:18080
TRAZA_PUBLIC_ORIGIN=http://18.118.112.206:18080
```

Si la IP pública es otra, se sustituye `18.118.112.206` en esas tres líneas. `.env` no se sube a Git.

## 6. Primera vez

Desde `~/fcdesign/FCDesign_client_server`:

```bash
docker compose -f compose.servidor.yaml build web
docker compose -f compose.servidor.yaml build runner
docker compose -f compose.servidor.yaml build frontend
docker compose -f compose.servidor.yaml up -d
```

La primera construcción tarda varios minutos. Al terminar, los siete servicios tienen que estar en marcha: `db`, `redis`, `runner`, `web`, `frontend` y `nginx`. Postgres y Redis no publican puertos hacia internet.

Comprobación dentro de la EC2:

```bash
curl -sS -m 10 http://127.0.0.1:18080/api/v1/auth/csrf/
```

Tiene que responder `{"ok":true}`. En el navegador se abre `http://18.118.112.206:18080`.

La cuenta que administra niveles no sale del alta pública:

```bash
docker compose -f compose.servidor.yaml exec web python manage.py create_admin --email admin@ejemplo.test --password 'una-clave-de-ocho-o-mas' --name "Administrador"
```

## 7. Cada cambio que ya está en main

Este es el ciclo que se repite en el servidor. No se editan archivos a mano en la EC2.

```bash
cd ~/fcdesign/FCDesign_client_server
git pull origin main
docker compose -f compose.servidor.yaml down
docker compose -f compose.servidor.yaml build web
docker compose -f compose.servidor.yaml build runner
docker compose -f compose.servidor.yaml build frontend
docker compose -f compose.servidor.yaml up -d
```

`down` para los contenedores y conserva los volúmenes `traza-db` y `traza-redis`. Las cuentas y los algoritmos siguen ahí. `down -v` los borra.

Si `git pull` dice que un archivo local impide el merge, ese cambio de la EC2 se descarta y se vuelve a jalar. El ejemplo que ya ocurrió fue `frontend/src/api.ts`:

```bash
git restore frontend/src/api.ts
git pull origin main
```

El código que vale es el de `origin/main`.

## 8. Si el sitio no abre

- La dirección lleva el puerto: `http://18.118.112.206:18080`. El 8080 no está abierto y el navegador se queda esperando.
- La IP `172.31.24.67` es privada. Desde fuera se usa la pública.
- El grupo de la instancia tiene que ser `launch-wizard-1`, con el TCP 18080 desde `0.0.0.0/0`.
- `docker compose -f compose.servidor.yaml ps` tiene que mostrar `nginx` en ejecución y el puerto `0.0.0.0:18080->80/tcp`.
