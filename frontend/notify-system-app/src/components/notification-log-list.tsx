import { Badge, Box, Flex, Stack, Text } from "@chakra-ui/react";

import type { NotificationLog } from "@/lib/api";
import { isOptimisticLogId } from "@/lib/notification-types";

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en-GB", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "UTC",
  }).format(new Date(value));
}

const statusMeta = {
  PENDING: {
    label: "Processing",
    colorPalette: "yellow",
  },
  SUCCESS: {
    label: "Delivered",
    colorPalette: "green",
  },
  FAILED: {
    label: "Failed",
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
        No delivery rows yet. Send a notification to see per-user and per-channel
        history.
      </Box>
    );
  }

  return (
    <Stack gap={3.5}>
      {logs.map((log) => {
        const isPreparing = isOptimisticLogId(log.id);

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
              <span>{log.category_name ?? "Unknown category"}</span>
              <Box as="span" w="5px" h="5px" rounded="full" bg="teal.300" />
              <span>
                {log.channel_name ??
                  (isPreparing ? "Resolving channels" : "Channel unavailable")}
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
                  ? `To ${log.user_name}`
                  : isPreparing
                    ? "Preparing deliveries"
                    : "No user on log"}
              </span>
              <time dateTime={log.created_at}>{formatDate(log.created_at)}</time>
            </Flex>
          </Box>
        );
      })}
    </Stack>
  );
}
