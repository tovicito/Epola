src_sources = [
  'main.py',
  'window.py',
  'managers.py',
  'app_info.py',
]

install_data(src_sources, install_dir: get_option('datadir') / 'epola')

gnome.compile_resources('epola',
  'epola.gresource.xml',
  gresource_bundle: true,
  install: true,
  install_dir: get_option('datadir') / 'epola',
)

python3 = import('python').find_installation()

conf = configuration_data()
conf.set('PYTHON', python3.full_path())
conf.set('VERSION', meson.project_version())
conf.set('localedir', get_option('prefix') / get_option('localedir'))
conf.set('pkgdatadir', get_option('prefix') / get_option('datadir') / 'epola')

configure_file(
  input: 'epola.in',
  output: 'epola',
  configuration: conf,
  install: true,
  install_dir: get_option('bindir'),
  install_mode: 'rwxr-xr-x'
)
