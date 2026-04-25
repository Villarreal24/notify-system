import { Badge, Box, Flex, Stack, Text } from "@chakra-ui/react";

import type { NotificationLog } from "@/lib/api";

function formatDate(value: string) {
  return new Intl.DateTimeFormat("es", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "UTC",
  }).format(new Date(value));
}

const statusMeta = {
  PENDING: {
    label: "Procesando",
    colorPalette: "yellow",
  },
  SUCCESS: {
    label: "Entregado",
    colorPalette: "green",
  },
  FAILED: {
    label: "Fallido",
    colorPalette: "red",
  },
} satisfies Record<
  NotificationLog["status"],
  { label: string; colorPalette: "yellow" | "green" | "red" }
>;

export function NotificationLogList({ logs }: { logs: NotificationLog[] }) {
  if (logs.length === 0) {
    return (
      <Box
        rounded="26px"
        borderWidth="1px"
        borderStyle="dashed"
        borderColor="whiteAlpha.300"
        bg="whiteAlpha.100"
        p={7}
        color="gray.400"
        lineHeight="1.7"
      >
        Aun no hay entregas registradas. Envia una notificacion para ver el
        historial por usuario y canal.
      </Box>
    );
  }

  return (
    <Stack gap={3.5}>
      {logs.map((log) => {
        const isPreparing = log.id.startsWith("optimistic-");

        return (
          <Box
            as="article"
            key={log.id}
            rounded="26px"
            borderWidth="1px"
            borderColor="whiteAlpha.200"
            bg="blackAlpha.500"
            p={5}
          >
            <Flex
              align="center"
              wrap="wrap"
              gap={2.5}
              color="gray.400"
              fontSize="xs"
              fontWeight="extrabold"
              letterSpacing="0.22em"
              textTransform="uppercase"
            >
              <span>{log.category_name ?? "Categoria eliminada"}</span>
              <Box as="span" w="5px" h="5px" rounded="full" bg="teal.300" />
              <span>
                {log.channel_name ??
                  (isPreparing ? "Preparando canales" : "Canal no disponible")}
              </span>
              <Badge
                colorPalette={statusMeta[log.status].colorPalette}
                rounded="full"
                px={2.5}
                letterSpacing="0.14em"
              >
                {statusMeta[log.status].label}
              </Badge>
            </Flex>
            <Text mt={3.5} color="white" lineHeight="1.6">
              {log.message}
            </Text>
            {log.error_message ? (
              <Text
                mt={3}
                rounded="xl"
                borderWidth="1px"
                borderColor="red.300/35"
                bg="red.950/35"
                p={3}
                color="red.100"
                fontSize="sm"
                lineHeight="1.6"
              >
                {log.error_message}
              </Text>
            ) : null}
            <Flex
              mt={4.5}
              justify="space-between"
              wrap="wrap"
              gap={3}
              color="gray.400"
              fontSize="xs"
            >
              <span>
                {log.user_name
                  ? `Para ${log.user_name}`
                  : isPreparing
                    ? "Preparando entregas"
                    : "Entrega sin usuario"}
              </span>
              <time dateTime={log.created_at}>{formatDate(log.created_at)}</time>
            </Flex>
          </Box>
        );
      })}
    </Stack>
  );
}
