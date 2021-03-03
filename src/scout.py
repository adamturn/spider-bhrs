# local modules
import jpm


def main():
    map_bucket = [
        jpm,
    ]
    for map in map_bucket:
        map.handle_sitemap()


    return None


if __name__ == "__main__":
    main()
