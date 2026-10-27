# Instalación del servidor en AWS

La instancia que ya está en marcha se llama `cfdesign`. Este manual sirve para crear otra igual y para volver a levantar el código cada vez que `main` cambia. El archivo de Word con el mismo contenido está en [Instalacion-servidor-AWS.docx](Instalacion-servidor-AWS.docx). El orden de los cambios, desde la primera configuración, está en [bitacora-instalacion-aws.md](bitacora-instalacion-aws.md).

El arranque del servidor es `compose.servidor.yaml`. Ese archivo no levanta Mailpit: el correo de confirmación sale por Gmail. El sitio público es `https://fcdesign.aulivana.com`. Nginx termina TLS y Django arranca con `config.settings.production`. La IP elástica, los puertos y el cierre del 18080 están en [Seguridad C1](#seguridad-c1).

## 1. La instancia que está hoy

Datos tomados de la consola de EC2. El tipo, la IP pública y los puertos se actualizaron el 26 de octubre de 2026, con C1.

| Dato | Valor |
| --- | --- |
| Nombre | cfdesign |
| ID | i-07c39f84b1c7b3787 |
| Región | EE. UU. Este (Ohio), `us-east-2` |
| Estado | En ejecución |
| Tipo | t3.small. El 21 de octubre de 2026 era t3.micro |
| AMI | ami-03e224e4dbc21f89e |
| Nombre de la AMI | al2023-ami-2023.12.20261014.0-kernel-6.18-x86_64 |
| Plataforma | Linux/UNIX, Amazon Linux 2023, x86_64 |
| Arranque | uefi |
| IMDSv2 | Obligatorio |
| VPC | vpc-0877ce6fabe7f919f |
| Subred | subnet-0065e8a11b4f527d8 |
| IP pública | la IP elástica. El 26 de octubre de 2026 el DNS de `fcdesign.aulivana.com` responde `77.112.213.200`. Antes, sin elástica, fue `3.17.151.210` y `18.118.112.206` |
| DNS público | `fcdesign.aulivana.com` |
| IP privada | 172.31.24.67. No cambia al asociar la elástica |
| IP elástica | asociada a esta instancia. Los pasos están en [Seguridad C1](#seguridad-c1) |
| Par de claves | cfdesign |
| Grupo de seguridad | launch-wizard-1, sg-05d3ffa45265dcd67 |
| Monitoreo detallado | desactivado |
| Protección de terminación | desactivada |

La IP privada `172.31.24.67` solo existe dentro de la VPC. El navegador usa la elástica, por el nombre `fcdesign.aulivana.com`.

El grupo `default` (sg-03438b97b419876e4) no es el de esta instancia. Las reglas que importan son las de `launch-wizard-1`.

| Puerto | Protocolo | Origen | Para qué |
| --- | --- | --- | --- |
| 22 | TCP | 0.0.0.0/0 | SSH, el acceso de administración |
| 80 | TCP | 0.0.0.0/0 | Nginx redirige a HTTPS y Let's Encrypt renueva el certificado |
| 443 | TCP | 0.0.0.0/0 | El sitio |
| 18080 | TCP | cerrado | El compose ya no lo publica. Hay que borrar la regla hacia internet |
| 8025 | TCP | cerrado | Mailpit no está en este compose. Hay que borrar la regla |

En una instancia nueva se abren el 22, el 80 y el 443. No se abre el 18080.

`t3.micro` tiene unos 913 MiB de memoria. Mientras Docker construye las imágenes, la sesión SSH puede cortarse con `Broken pipe`. Se vuelve a entrar y se repite el comando que quedó a medias. En esta instancia hizo falta un archivo de intercambio de 2 GB antes de que la construcción terminara. Los comandos están en la sección 6. Una `t3.small` deja más margen.

## 2. Crear la instancia

En la consola de AWS, región **Ohio (us-east-2)**:

1. EC2 → Instancias → Lanzar instancias.
2. Nombre: `cfdesign`.
3. AMI: Amazon Linux 2023, kernel 6.x, arquitectura 64 bits (x86). La de esta máquina es `ami-03e224e4dbc21f89e`. Una Amazon Linux 2023 posterior, de 64 bits, también sirve.
4. Tipo: `t3.micro`.
5. Par de claves: crear o elegir `cfdesign` y guardar el archivo `cfdesign.pem`.
6. Red: la VPC y la subred de la tabla, con IP pública automática. Después se sustituye por la elástica, en [Seguridad C1](#seguridad-c1).
7. Grupo de seguridad nuevo, o `launch-wizard-1` si ya existe. Entrada TCP 22, TCP 80 y TCP 443 desde `0.0.0.0/0`. Sin 18080 y sin 8025.
8. Almacenamiento: el volumen por defecto del asistente.
9. Metadatos: IMDSv2 obligatorio.
10. Lanzar.

Desde el Mac, con el `.pem` en la carpeta desde la que se trabaja:

```bash
chmod 400 cfdesign.pem
ssh -i "cfdesign.pem" ec2-user@77.112.213.200
```

Esa es la elástica del 26 de octubre de 2026. Si es otra, se usa la que muestre la consola. El usuario es `ec2-user`.

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
DJANGO_SECRET_KEY=una-clave-larga-distinta-de-las-de-desarrollo
EMAIL_HOST_PASSWORD=clave-de-aplicacion-de-gmail
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,web,nginx,fcdesign.aulivana.com
DJANGO_CSRF_ORIGINS=https://fcdesign.aulivana.com
TRAZA_PUBLIC_ORIGIN=https://fcdesign.aulivana.com
```

`DJANGO_SECRET_KEY` no puede quedar vacía ni ser `dev-only-change-me` ni `dev-container-not-production`. Con una de esas, `config.settings.production` no arranca. `DJANGO_CSRF_ORIGINS` tiene que ser `https://`. `.env` no se sube a Git. Si esas variables no están, `compose.servidor.yaml` usa `https://fcdesign.aulivana.com`. La aplicación de escritorio, si no tiene `TRAZA_API_ORIGIN`, tiene que llamar a ese mismo origen.

## 6. Primera vez

El archivo que se usa es `compose.servidor.yaml`. `docker compose up` sin `-f` lee `compose.yaml`, que es el de desarrollo: levanta Vite y Mailpit y no es este servidor.

Antes de construir, en esta `t3.micro`, se deja un intercambio de 2 GB. Sin él, el build se queda sin memoria. La línea de `fstab` lo conserva al reiniciar:

```bash
sudo dd if=/dev/zero of=/swapfile bs=1M count=2048
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

`swapon --show` tiene que listar `/swapfile`. Si el archivo ya existe, no se vuelve a crear.

Desde `~/fcdesign/FCDesign_client_server`:

```bash
docker compose -f compose.servidor.yaml build web
docker compose -f compose.servidor.yaml build runner
docker compose -f compose.servidor.yaml build nginx
docker compose -f compose.servidor.yaml build languages
docker compose -f compose.servidor.yaml up -d --remove-orphans
```

No se construye `frontend`. `languages` es el contenedor de C y de los demás lenguajes del navegador. No lleva las claves y no tiene salida a internet. La primera construcción descarga Node, Java y .NET; tarda más que las otras. Ese servicio era el Vite de desarrollo. Nginx incluye la página ya construida. `--remove-orphans` apaga un contenedor `frontend` que hubiera quedado de un arranque anterior.

La primera construcción tarda varios minutos. Al terminar tienen que estar en marcha `db`, `redis`, `runner`, `web` y `nginx`. Postgres y Redis no publican puertos hacia internet.

Comprobación dentro de la EC2:

```bash
curl -sS -m 10 https://fcdesign.aulivana.com/api/v1/auth/csrf/
```

Tiene que responder `{"ok":true}` y la cookie `csrftoken` tiene que llevar `Secure`. En el navegador se abre `https://fcdesign.aulivana.com`. `http://` en el puerto 80 responde con una redirección a ese mismo nombre. Nginx no arranca si todavía no existe el certificado de la sección [Seguridad C1](#seguridad-c1).

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
docker compose -f compose.servidor.yaml build nginx
docker compose -f compose.servidor.yaml build languages
docker compose -f compose.servidor.yaml up -d --remove-orphans
```

`down` para los contenedores y conserva los volúmenes `traza-db` y `traza-redis`. Las cuentas y los algoritmos siguen ahí. `down -v` los borra.

Si el disco se llena, `df -h` lo muestra y `docker system df` dice qué ocupa Docker. `docker builder prune -f` borra la caché de construcción y deja las imágenes en uso. `docker system prune -af` borra además las imágenes que no están en marcha: el siguiente `build` empieza de cero. No borra los volúmenes `traza-db` y `traza-redis`.

Si `git pull` dice que un archivo local impide el merge, ese cambio de la EC2 se descarta y se vuelve a jalar. El ejemplo que ya ocurrió fue `frontend/src/api.ts`:

```bash
git restore frontend/src/api.ts
git pull origin main
```

El código que vale es el de `origin/main`.

## 8. Si el sitio no abre

- La dirección es `https://fcdesign.aulivana.com`, sin `:18080`. El 8080 y el 18080 no son el sitio.
- `http://fcdesign.aulivana.com` tiene que redirigir a `https://`. Si el navegador se queda en HTTP, el puerto 80 no está abierto o Nginx no cargó.
- La IP `172.31.24.67` es privada. Desde fuera se usa la elástica, y el DNS del dominio tiene que apuntar a ella.
- El grupo de la instancia tiene que ser `launch-wizard-1`, con TCP 22, 80 y 443. Sin regla de 18080 hacia internet.
- `docker compose -f compose.servidor.yaml ps` tiene que mostrar `nginx` con `0.0.0.0:80->80/tcp` y `0.0.0.0:443->443/tcp`.
- Si Nginx reinicia en bucle, faltan `/etc/letsencrypt/live/fcdesign.aulivana.com/fullchain.pem` y `privkey.pem` en el host.
- Si `df -h` deja el disco casi lleno, se aplica la limpieza de la sección 7 y se repite el build. El volumen de 30 GB de la consola no se ve en `df` hasta estirar la partición, en [Seguridad C1](#seguridad-c1).

## Seguridad C1

| Campo | Valor |
| --- | --- |
| ID | C1 |
| Gravedad | Crítico |
| Zona | Servidor |
| Hallazgo | El servidor público arranca en modo desarrollo y sin TLS |
| Corrección | Poner TLS delante de Nginx, apuntar `DJANGO_SETTINGS_MODULE` a `config.settings.production`, exigir una clave distinta de los valores de desarrollo, alargar HSTS y declarar el proxy de confianza. En el firewall del host dejar solo 443 y el acceso de administración; cerrar 18080 hacia internet |

Eso ya está en el código de `main` y en la instancia que responde `https://fcdesign.aulivana.com`. Esta sección es el procedimiento para dejar otra instancia igual, desde la IP elástica hasta el certificado.

### Crear la IP elástica y asignarla

En la consola de EC2, región **Ohio (us-east-2)**:

1. **Red y seguridad → Direcciones IP elásticas → Asignar dirección IP elástica**.
2. Grupo de direcciones: IPv4 de Amazon. Borde de red: esta región. **Asignar**.
3. Anotar la dirección nueva. Esa es la pública fija.
4. Marcarla → **Acciones → Asociar dirección IP elástica**.
5. Tipo de recurso: **Instancia**. Instancia: `cfdesign` (`i-07c39f84b1c7b3787`).
6. IP privada: `172.31.24.67`.
7. **Asociar**.

La IP automática que tenía la instancia se suelta en ese momento. La elástica sigue aunque la instancia se detenga. La privada no cambia. El nombre `fcdesign.aulivana.com` se publica en GoDaddy, en el paso siguiente. Sin ese registro, Let's Encrypt no emite el certificado.

### El dominio en GoDaddy

El DNS de `aulivana.com` está en GoDaddy. Los servidores de nombres son `ns55.domaincontrol.com` y `ns56.domaincontrol.com`. El registro no se crea en Route 53 ni en la consola de EC2.

1. Entra en [godaddy.com](https://www.godaddy.com) con la cuenta que registró el dominio.
2. Abre **Mis productos** y elige **aulivana.com**.
3. Entra en **DNS** (a veces aparece como **Administrar DNS**).
4. En **Registros DNS**, pulsa **Agregar**.
5. Llena el registro así:

| Campo | Valor |
| --- | --- |
| Tipo | A |
| Nombre | `fcdesign` |
| Valor | la IP elástica asociada a `cfdesign`. El 26 de octubre de 2026 es `77.112.213.200` |
| TTL | 1 hora, el valor por defecto |

El nombre es solo `fcdesign`. Si se escribe `fcdesign.aulivana.com`, GoDaddy lo publica como `fcdesign.aulivana.com.aulivana.com`.

Guarda cuando la elástica ya esté asociada. Si el registro apunta a una IP que todavía no está unida a la instancia, el dominio no llega al sitio. Un subdominio no se cobra aparte: el dominio `aulivana.com` ya está pagado.

La comprobación, desde cualquier máquina:

```bash
dig +short A fcdesign.aulivana.com
```

Tiene que imprimir la misma IP elástica de la consola de EC2.

La IP pública cuesta 0.005 dólares por hora y sale de los créditos del plan gratuito. La elástica asociada a la instancia en marcha sustituye a la automática: no se suman las dos. Si la elástica queda asignada a la cuenta y no asociada a una instancia en marcha, el cargo sigue.

### Puertos

El firewall que ve internet es el grupo `launch-wizard-1` (`sg-05d3ffa45265dcd67`). En **Instancia → Seguridad → grupos de seguridad**, las reglas de entrada quedan así:

| Puerto | Se deja | Motivo |
| --- | --- | --- |
| 22 | Sí | Administración por SSH |
| 443 | Sí | HTTPS. Nginx escucha aquí |
| 80 | Sí | Excepción práctica: la redirección a HTTPS y la renovación del certificado. C1 pide dejar solo 443 y la administración; sin el 80, Let's Encrypt no renueva |
| 18080 | No | Se borra la regla hacia `0.0.0.0/0`. `compose.servidor.yaml` publica `80:80` y `443:443`, no el 18080 |
| 8025 | No | Se borra. Este compose no publica Mailpit |
| 5432 y 6379 | No | Postgres y Redis no tienen puerto en el host |

En la instancia, si `systemctl is-active firewalld` responde `active`, el mismo criterio: SSH, HTTP y HTTPS. Si responde `inactive`, manda solo el grupo de seguridad.

El volumen de la consola puede decir 30 GB mientras `df -h /` sigue en 8 GB. Eso no es el firewall. En la instancia:

```bash
sudo growpart /dev/nvme0n1 1
sudo xfs_growfs -d /
df -h /
```

### TLS y producción

`deploy/nginx/servidor.conf` escucha 443 con el certificado de `fcdesign.aulivana.com` y redirige el puerto 80 a `https://fcdesign.aulivana.com`. `/api/` y `/admin/` van a Gunicorn por HTTP interno, con `X-Forwarded-Proto $scheme`. El certificado tiene que existir en el host antes de `docker compose up`, porque Nginx no arranca sin estos dos archivos:

- `/etc/letsencrypt/live/fcdesign.aulivana.com/fullchain.pem`
- `/etc/letsencrypt/live/fcdesign.aulivana.com/privkey.pem`

Con el puerto 80 libre (el compose todavía no está arriba):

```bash
sudo dnf install -y certbot
sudo mkdir -p /var/www/certbot
sudo certbot certonly --standalone -d fcdesign.aulivana.com --agree-tos -m correo-del-responsable --non-interactive
```

`compose.servidor.yaml` monta `/etc/letsencrypt` y `/var/www/certbot` en Nginx, y fija:

```bash
DJANGO_SETTINGS_MODULE=config.settings.production
```

Ese módulo, en `server/config/settings/production.py`, hace el resto de C1:

- `DEBUG` queda en falso. Las cookies de sesión y de CSRF salen con `Secure`.
- Rechaza `DJANGO_SECRET_KEY` vacía, `dev-only-change-me` y `dev-container-not-production`.
- Exige `DJANGO_CSRF_ORIGINS` en `https://` y `TRAZA_RUNNER=redis`.
- `SECURE_PROXY_SSL_HEADER` confía en `X-Forwarded-Proto: https`. Sin eso, Django creería que la petición sigue en HTTP y no guardaría la sesión.
- `SECURE_HSTS_SECONDS` está en `3600` (una hora), con subdominios. C1 pide alargarlo cuando el inicio de sesión por HTTPS ya se comprobó. El valor de un año es `31536000`, en esa misma línea. Subirlo antes deja al navegador atado a este nombre si el certificado falla.
- La caché del bloqueo de intentos usa Redis, la misma `REDIS_URL` del compose.

La comprobación, desde fuera:

```bash
curl -sI https://fcdesign.aulivana.com/api/v1/auth/csrf/
```

Tiene que verse `strict-transport-security` y `set-cookie` con `Secure`. La aplicación de escritorio usa el mismo origen: `https://fcdesign.aulivana.com`, en `desktop/src-tauri/src/lib.rs` o en `TRAZA_API_ORIGIN`. Un instalador que siga en `http://…:18080` no guarda la cookie segura.

Para renovar el certificado sin soltar el puerto 80, en `/etc/letsencrypt/renewal/fcdesign.aulivana.com.conf` el authenticator queda en `webroot` y `webroot_path` en `/var/www/certbot`. Nginx ya sirve `/.well-known/acme-challenge/` desde esa carpeta. Después:

```bash
sudo certbot renew --dry-run
docker compose -f compose.servidor.yaml exec nginx nginx -s reload
```
